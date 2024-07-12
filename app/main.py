import psycopg2
from flask import Flask, jsonify, send_file, url_for, render_template_string
import os
import json

# create the Flask app
app = Flask(__name__)

# Function to create the stored function in the database
def create_select_function():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        port=os.environ.get("DB_PORT"),
    )
    with conn.cursor() as cur:
        create_function_query = """
        CREATE OR REPLACE FUNCTION select_tables_within_county(grid_value text)
        RETURNS TABLE(table_name text, record jsonb) AS $$
        DECLARE
            table_rec RECORD;
            sql_query text;
        BEGIN
            FOR table_rec IN 
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                AND tablename != 'spatial_ref_sys'
            LOOP
                sql_query := format('
                    SELECT 
                        %L AS table_name,
                        jsonb_agg(t.*) AS record
                    FROM 
                        %I t
                    JOIN (
                        SELECT ST_Transform(shape, 4326) AS shape_4326 
                        FROM grd 
                        WHERE grid = %L
                    ) county 
                    ON ST_Contains(county.shape_4326, ST_Transform(t.shape, 4326))
                ', table_rec.tablename, table_rec.tablename, grid_value);
                
                RETURN QUERY EXECUTE sql_query;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
        """
        cur.execute(create_function_query)
        conn.commit()
    conn.close()

# create the index route
@app.route('/')
def index():
    return "The API is working!"

# create a general DB to GeoJSON function based on a SQL query
def database_to_geojson_by_query(sql_query, grid):
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        port=os.environ.get("DB_PORT"),
    )
    with conn.cursor() as cur:
        cur.execute(sql_query)
        rows = cur.fetchall()
    conn.close()

    geojson_files = []

    for row in rows:
        table_name = row[0]
        records = row[1]
        features = []

        for record in records:
            feature = {
                "type": "Feature",
                "geometry": record["shape"],
                "properties": {k: v for k, v in record.items() if k != "shape"}
            }
            feature["properties"]["table_name"] = table_name
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        # Save each table's data into a separate GeoJSON file
        filename = f"{grid}_{table_name}.geojson"
        with open(filename, 'w') as f:
            json.dump(geojson, f)

        geojson_files.append(filename)

    return geojson_files

# Route to generate and list GeoJSON files with download links
@app.route('/<grid>', methods=['GET'])
def get_json(grid):
    sql_query = f"SELECT * FROM select_tables_within_county('{grid}');"
    geojson_files = database_to_geojson_by_query(sql_query, grid)
    
    # Generate download URLs for the files
    file_links = [{
        "name": os.path.splitext(filename)[0],
        "url": url_for('download_file', filename=filename, _external=True, _scheme='https')
    } for filename in geojson_files]

    # Generate HTML links for easy clicking
    html_links = ''.join([f'<li><a href="{file["url"]}">{file["name"]}</a></li>' for file in file_links])

    # Return an HTML page with clickable links
    return render_template_string(f"""
    <html>
        <body>
            <h1>Download GeoJSON Files</h1>
            <ul>
                {html_links}
            </ul>
        </body>
    </html>
    """)

# Route to download a specific GeoJSON file
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    create_select_function()  # Create the function when the app starts
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
