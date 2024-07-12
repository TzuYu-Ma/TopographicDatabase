import psycopg2
import shapefile
from flask import Flask, send_file, jsonify
import os
from io import BytesIO
import zipfile

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

# Function to convert database records to shapefiles
def records_to_shapefile(table_name, records):
    shp_io = BytesIO()
    shp = shapefile.Writer(shp_io, shapeType=shapefile.POLYGON)

    # Assuming all records have the same fields
    fields = records[0].keys()
    for field in fields:
        if field != 'shape':
            shp.field(field, 'C')

    for record in records:
        attributes = [record[field] for field in fields if field != 'shape']
        shp.record(*attributes)
        geom = record['shape']['coordinates']
        shp.poly([geom])

    shp.close()

    zip_io = BytesIO()
    with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for ext in ['shp', 'shx', 'dbf']:
            zipf.writestr(f"{table_name}.{ext}", shp_io.getvalue())
    zip_io.seek(0)

    return zip_io

# call our general function with the provided grid
@app.route('/<grid>', methods=['GET'])
def get_shapefiles(grid):
    sql_query = f"SELECT * FROM select_tables_within_county('{grid}');"
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

    shapefiles = {}
    for row in rows:
        table_name = row[0]
        records = row[1]
        shapefiles[table_name] = records_to_shapefile(table_name, records)

    zip_io = BytesIO()
    with zipfile.ZipFile(zip_io, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for table_name, shapefile_io in shapefiles.items():
            for ext in ['shp', 'shx', 'dbf']:
                zipf.writestr(f"{table_name}/{table_name}.{ext}", shapefile_io.read())
    zip_io.seek(0)

    return send_file(zip_io, mimetype='application/zip', as_attachment=True, download_name='shapefiles.zip')

if __name__ == "__main__":
    create_select_function()  # Create the function when the app starts
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
