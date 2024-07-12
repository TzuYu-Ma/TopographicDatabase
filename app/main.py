import psycopg2
from flask import Flask, jsonify, send_file, url_for, render_template_string
import os
import json
import zipfile
import logging

# create the Flask app
app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.DEBUG)

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
    try:
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
    
    except Exception as e:
        logging.error(f"Error in database_to_geojson_by_query: {e}")
        raise

# Route to generate and list GeoJSON files with download links
@app.route('/<grid>', methods=['GET'])
def get_json(grid):
    try:
        sql_query = f"SELECT * FROM select_tables_within_county('{grid}');"
        geojson_files = database_to_geojson_by_query(sql_query, grid)
        
        # Generate download URLs for the files
        file_links = [{
            "name": os.path.splitext(filename)[0],
            "url": url_for('download_file', filename=filename, _external=True, _scheme='https')
        } for filename in geojson_files]

        # Generate HTML links for easy clicking
        html_links = ''.join([f'<li><a href="{file["url"]}">{file["name"]}</a></li>' for file in file_links])

        # Add link for downloading all files as a ZIP archive
        zip_url = url_for('download_all_files', grid=grid, _external=True, _scheme='https')
        zip_link = f'<li><a href="{zip_url}">Download All as ZIP</a></li>'

        # Return an HTML page with clickable links
        return render_template_string(f"""
        <html>
            <body>
                <h1>Download GeoJSON Files</h1>
                <ul>
                    {html_links}
                    {zip_link}
                </ul>
            </body>
        </html>
        """)
    
    except Exception as e:
        logging.error(f"Error in get_json: {e}")
        return "Internal Server Error", 500

# Route to download a specific GeoJSON file
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logging.error(f"Error in download_file: {e}")
        return "Internal Server Error", 500

# Route to download all GeoJSON files as a ZIP archive
@app.route('/download_all/<grid>', methods=['GET'])
def download_all_files(grid):
    try:
        sql_query = f"SELECT * FROM select_tables_within_county('{grid}');"
        geojson_files = database_to_geojson_by_query(sql_query, grid)
        
        zip_filename = f"{grid}_geojson_files.zip"
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for geojson_file in geojson_files:
                zipf.write(geojson_file)
        
        return send_file(zip_filename, as_attachment=True)
    
    except Exception as e:
        logging.error(f"Error in download_all_files: {e}")
        return "Internal Server Error", 500

if __name__ == "__main__":
    create_select_function()  # Create the function when the app starts
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
