import psycopg2
from flask import Flask, jsonify
import os

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
        CREATE OR REPLACE FUNCTION select_tables_within_county(grid_param text)
        RETURNS TABLE (
            builda_id integer,
            builda_geometry json,
            county_id integer,
            county_geometry json
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH 
            county AS (
                SELECT *, ST_Transform(shape, 4326) AS shape_4326 
                FROM grd 
                WHERE grid = grid_param
            ),
            builda_transformed AS (
                SELECT *, ST_Transform(shape, 4326) AS shape_4326
                FROM builda
            )
            SELECT 
                builda_transformed.id,
                ST_AsGeoJSON(builda_transformed.shape_4326)::json AS builda_geometry,
                county.id,
                ST_AsGeoJSON(county.shape_4326)::json AS county_geometry
            FROM 
                builda_transformed
            JOIN 
                county 
            ON 
                ST_Contains(county.shape_4326, builda_transformed.shape_4326);
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
def database_to_geojson_by_query(sql_query):
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

    features = []
    for row in rows:
        feature = {
            "type": "Feature",
            "properties": {
                "builda_id": row[0],
                "county_id": row[2],
            },
            "geometry": row[1]
        }
        features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    return jsonify(geojson)

# call our general function with the provided grid
@app.route('/<grid>', methods=['GET'])
def get_json(grid):
    sql_query = f"SELECT * FROM select_tables_within_county('{grid}');"
    grid_geojson = database_to_geojson_by_query(sql_query)
    return grid_geojson

if __name__ == "__main__":
    create_select_function()  # Create the function when the app starts
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
