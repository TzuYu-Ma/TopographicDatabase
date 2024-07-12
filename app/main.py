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

    if not rows:
        print("No rows returned from the query")
    else:
        print(f"Rows returned: {len(rows)}")

    features = []
    for row in rows:
        table_name = row[0]
        records = row[1]
        if records:  # Ensure records is not None
            for record in records:
                if "geometry" in record:
                    feature = {
                        "type": "Feature",
                        "geometry": record["geometry"],
                        "properties": {key: value for key, value in record.items() if key != "geometry"}
                    }
                    feature["properties"]["table_name"] = table_name
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
    print(f"Executing SQL query: {sql_query}")
    grid_geojson = database_to_geojson_by_query(sql_query)
    return grid_geojson

if __name__ == "__main__":
    create_select_function()  # Create the function when the app starts
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
