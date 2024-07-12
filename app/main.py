import psycopg2
from flask import Flask, send_file
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

# create a function to convert SQL query result to GeoJSON and save to a file
def save_geojson_by_query(sql_query, grid_value):
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
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        filename = f"{grid_value}_{table_name}.geojson"
        with open(filename, 'w') as f:
            json.dump(geojson, f)

        yield filename

# endpoint to generate and download GeoJSON files
@app.route('/download/<grid>', methods=['GET'])
def download_geojson(grid):
    sql_query = f"SELECT * FROM select_tables_within_county('{grid}');"
    filenames = list(save_geojson_by_query(sql_query, grid))
    return jsonify({"files": filenames})

# endpoint to serve generated GeoJSON files
@app.route('/files/<filename>', methods=['GET'])
def serve_file(filename):
    return send_file(filename)

if __name__ == "__main__":
    create_select_function()  # Create the function when the app starts
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
