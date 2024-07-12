import psycopg2
from flask import Flask, jsonify, send_file, url_for, render_template_string
import os
import json
import zipfile
import logging

# create the Flask app
app = Flask(__name__)

# Set up logging
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
        CREATE OR REPLACE FUNCTION select_tables_within_area(area_value text, area_type text)
        RETURNS TABLE(table_name text, record jsonb) AS $$
        DECLARE
            table_rec RECORD;
            sql_query text;
            column_name text;
        BEGIN
            -- 根據 area_type 設置列名
            IF area_type = 'grd' THEN
                column_name := 'grid';
            ELSIF area_type = 'county_boundary' THEN
                column_name := 'countycode';
            ELSE
                RAISE EXCEPTION 'Invalid area_type: %', area_type;
            END IF;

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
                        FROM %I 
                        WHERE %I = %L
                    ) area 
                    ON ST_Contains(area.shape_4326, ST_Transform(t.shape, 4326))
                ', table_rec.tablename, table_rec.tablename, area_type, column_name, area_value);
                
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
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>二萬五千分之一圖幅圖號</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f4f4f9;
                margin: 0;
                padding: 20px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                text-align: center;
            }
            h1 {
                color: #333;
            }
            p {
                font-size: 1.2em;
                color: #666;
                max-width: 600px;
            }
            .container {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>二萬五千分之一圖幅圖號</h1>
            <p>此網頁提供 GeoJson 格式供下載，請參照圖幅圖號，將所需圖號複製到網址欄後並按 Enter。</p>
            <p>例: 若需要 93203NW 圖號圖資，請在網址欄最右邊加上 "/93203NW"</p>
        </div>
    </body>
    </html>
    """)

# create a general DB to GeoJSON function based on a SQL query
def database_to_geojson_by_query(sql_query, area):
    try:
        logging.debug(f"Executing SQL query: {sql_query}")
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

        if not rows:
            logging.error(f"No rows returned for query: {sql_query}")
            return []

        geojson_files = []

        for row in rows:
            table_name = row[0]
            records = row[1]
            if not records:
                logging.warning(f"No records found for table: {table_name}")
                continue

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
            filename = f"{area}_{table_name}.geojson"
            with open(filename, 'w') as f:
                json.dump(geojson, f)

            geojson_files.append(filename)

        return geojson_files

    except Exception as e:
        logging.error(f"Error in database_to_geojson_by_query: {e}")
        return []

# Route to generate and list GeoJSON files with download links
@app.route('/<area>', methods=['GET'])
def get_json(area):
    try:
        area_type = 'grd' if area.isdigit() else 'county_boundary'
        sql_query = f"SELECT * FROM select_tables_within_area('{area}', '{area_type}');"
        geojson_files = database_to_geojson_by_query(sql_query, area)
        
        if not geojson_files:
            logging.error(f"No GeoJSON files generated for area: {area}")
            return "No GeoJSON files generated", 500

        # Generate download URLs for the files
