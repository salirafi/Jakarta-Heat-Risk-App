"""
Build and save Jakarta ward (kelurahan) boundary data from RBI geodatabase from Badan Informasi Geospasial.
Saving is done to SQLite.

.gdb file for the ward boundary polygon data is downloaded from https://geoservices.big.go.id/portal/apps/webappviewer/index.html?id=cb58db080712468cb4bfd408dbde3d70
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import fiona
import geopandas as gpd
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]

REFERENCE_CSV = BASE_DIR / "jakarta_reference.csv"
DB_PATH = BASE_DIR / "tables" / "heat_risk.db"

GDB_PATH = Path(r"RBI10K_ADMINISTRASI_DESA_20230928.gdb")
OUTPUT_TABLE = "jakarta_kelurahan_boundary"
# layer's name can be checked with the following code: print(fiona.listlayers(gdb_path)); see list_gdb_layers() function below
GDB_LAYER = "ADMINISTRASI_AR_DESAKEL"

# the name for Jakarta in the GDB is "Kota Adm. Jakarta xxx"
JAKARTA_CITIES = {
    "KOTA ADM JAKARTA PUSAT",
    "KOTA ADM JAKARTA UTARA",
    "KOTA ADM JAKARTA BARAT",
    "KOTA ADM JAKARTA SELATAN",
    "KOTA ADM JAKARTA TIMUR",
}

def clean_text(value: object) -> str | None:
    """Normalize text for safer matching across files."""
    if value is None:
        return None
    # remove dots to avoid mismatches like "KEL. TANJUNG DUREN UTARA" vs "KEL TANJUNG DUREN UTARA"
    # also strip whitespace and convert to uppercase for case-insensitive matching
    return str(value).strip().upper().replace(".", "")


def list_gdb_layers(gdb_path: Path) -> list[str]:
    """Return available layers inside the GDB."""
    return fiona.listlayers(str(gdb_path))

# this is at desa/kelurahan level, so the code is the most granular one (adm4)
def load_boundary_layer(gdb_path: Path, layer: str) -> gpd.GeoDataFrame:
    """Load the desa/kelurahan boundary layer and keep only needed columns"""
    gdf = gpd.read_file(str(gdb_path), layer=layer)

    # keep only useful columns and the geometry
    gdf = gdf[
        [
            "NAMOBJ",
            "KDEPUM",
            "WADMKD",
            "WADMKC",
            "WADMKK",
            "WADMPR",
            "geometry",
        ]
    ].copy()

    for col in ["NAMOBJ", "WADMKD", "WADMKC", "WADMKK", "WADMPR", "KDEPUM"]:
        gdf[col] = gdf[col].astype(str).str.strip() # ensure all are strings and remove leading/trailing whitespace

    # create cleaned versions of the relevant columns for matching purposes
    gdf["desa_clean"] = gdf["WADMKD"].apply(clean_text)
    gdf["kecamatan_clean"] = gdf["WADMKC"].apply(clean_text)
    gdf["kotkab_clean"] = gdf["WADMKK"].apply(clean_text)
    gdf["provinsi_clean"] = gdf["WADMPR"].apply(clean_text)
    gdf["kdepum_clean"] = gdf["KDEPUM"].astype(str).str.strip()

    return gdf

def filter_jakarta_boundaries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep only DKI Jakarta administrative areas."""
    return gdf[
        (gdf["provinsi_clean"] == "DKI JAKARTA")
        & (gdf["kotkab_clean"].isin(JAKARTA_CITIES))
    ].copy()


def load_reference_csv(path: Path) -> pd.DataFrame:
    """Load and clean the regional reference file used elsewhere in the project."""
    ref_df = pd.read_csv(path, dtype=str)

    # do the same cleaning for the reference file to ensure better matching with the GDB data
    for col in ["adm4", "desa_kelurahan", "kecamatan", "kotkab", "provinsi"]:
        ref_df[col] = ref_df[col].astype(str).str.strip()

    ref_df["desa_clean"] = ref_df["desa_kelurahan"].apply(clean_text)
    ref_df["kecamatan_clean"] = ref_df["kecamatan"].apply(clean_text)
    ref_df["kotkab_clean"] = ref_df["kotkab"].apply(clean_text)
    ref_df["provinsi_clean"] = ref_df["provinsi"].apply(clean_text)
    ref_df["adm4_clean"] = ref_df["adm4"].astype(str).str.strip()

    return ref_df

# this function is not used in the main pipeline but can be helpful for diagnostics to see how well the GDB and reference CSV align on codes and names
# it prints the number of matches based on codes and hierarchical names, and also lists any codes that are present in one source but not the other
# this can help identify if there are any discrepancies in the data sources that need to be addressed before saving the final boundary table
def print_matching_diagnostics(
    gdf_jakarta: gpd.GeoDataFrame,
    ref_df: pd.DataFrame,
) -> None:
    """Print simple diagnostics to verify code and name alignment."""

    # check how many rows match based on the cleaned adm4 code, which is the most specific code for desa/kelurahan level
    code_match = gdf_jakarta.merge(
        ref_df,
        left_on="kdepum_clean",
        right_on="adm4_clean",
        how="inner",
    )

    # the number of matches based on code should ideally be equal to the total number of rows in the reference CSV, 
    # since both are supposed to represent the same set of kelurahan in Jakarta
    print(f"Code matches: {len(code_match)}")
    if not code_match.empty:
        print(code_match[["KDEPUM", "adm4", "WADMKD", "desa_kelurahan"]].head(20))

    gdb_codes = set(gdf_jakarta["kdepum_clean"].dropna().unique())
    ref_codes = set(ref_df["adm4_clean"].dropna().unique())

    only_in_ref = sorted(ref_codes - gdb_codes)
    only_in_gdb = sorted(gdb_codes - ref_codes)

    print("In reference but not in GDB:", only_in_ref) # ideally should be empty if the GDB has all the same kelurahan as the reference CSV
    print("In GDB but not in reference:", only_in_gdb) # ideally should be empty if the GDB and reference CSV are mostly aligned; 
    # if there are many codes here, it may indicate that the GDB has additional kelurahan that are not in the reference CSV, 
    # or that there are discrepancies in the codes used between the two sources

# this function takes the filtered Jakarta GeoDataFrame and constructs a new DataFrame that is suitable for saving into SQLite
def build_boundary_table(gdf_jakarta: gpd.GeoDataFrame) -> pd.DataFrame:
    """Convert Jakarta boundaries into a SQLite-friendly table with WKT geometry."""
    gdf_wgs84 = gdf_jakarta.to_crs(epsg=4326).copy() # ensure it's in WGS84 for easier use later
    gdf_wgs84["geometry_wkt"] = gdf_wgs84.geometry.to_wkt() # convert geometry to WKT format for easier storage in SQLite; this will allow to read it back as text and convert to geometry later when needed

    # keep only the relevant columns (omitting 'NAMOBJ' and 'geomtery' columns)
    boundary_df = gdf_wgs84[
        [
            "KDEPUM",
            "WADMKD",
            "WADMKC",
            "WADMKK",
            "WADMPR",
            "geometry_wkt",
        ]
    ].copy()

    # rename columns to match the name formatting in BMKG data
    boundary_df = boundary_df.rename(
        columns={
            "KDEPUM": "adm4",
            "WADMKD": "desa_kelurahan",
            "WADMKC": "kecamatan",
            "WADMKK": "kotkab",
            "WADMPR": "provinsi",
        }
    )

    boundary_df["adm4"] = boundary_df["adm4"].astype(str).str.strip()
    boundary_df = boundary_df.drop_duplicates(subset=["adm4"]).reset_index(drop=True)
    return boundary_df

def save_boundary_table(boundary_df: pd.DataFrame, db_path: Path, table_name: str) -> None:
    """Write the boundary table into SQLite, replacing any older version"""
    with sqlite3.connect(db_path) as conn:
        boundary_df.to_sql(table_name, conn, if_exists="replace", index=False) # should be replace not append, since we want to overwrite any old version of the table

def preview_saved_table(db_path: Path, table_name: str, limit: int = 10) -> None:
    """Print row count and a small preview from SQLite"""
    with sqlite3.connect(db_path) as conn:
        count_df = pd.read_sql_query(
            f"SELECT COUNT(*) AS n FROM {table_name}",
            conn,
        )
        print(count_df)

        sample_df = pd.read_sql_query(
            f"""
            SELECT adm4, desa_kelurahan, kecamatan, kotkab
            FROM {table_name}
            LIMIT {limit}
            """,
            conn,
        )
        print(sample_df)

def main() -> None:
    print("=== Available GDB layers ===")
    layers = list_gdb_layers(GDB_PATH)
    print(layers)

    print("\n=== Load boundary layer ===")
    gdf = load_boundary_layer(GDB_PATH, GDB_LAYER)
    print(gdf.head())
    print("CRS:", gdf.crs)
    print("Geometry types:", gdf.geom_type.unique())
    print("Total rows:", len(gdf))

    print("\n=== Filter Jakarta only ===")
    gdf_jakarta = filter_jakarta_boundaries(gdf)
    print("Total Indonesia rows:", len(gdf))
    print("Jakarta-only rows:", len(gdf_jakarta))

    print("\n=== Load reference CSV ===")
    ref_df = load_reference_csv(REFERENCE_CSV)
    print(f"Reference rows: {len(ref_df)}")

    print("\n=== Matching diagnostics ===")
    print_matching_diagnostics(gdf_jakarta, ref_df)

    print("\n=== Build boundary table ===")
    boundary_df = build_boundary_table(gdf_jakarta)
    print(boundary_df.head())
    print(f"Boundary rows to save: {len(boundary_df)}")

    print("\n=== Save to SQLite ===")
    save_boundary_table(boundary_df, DB_PATH, OUTPUT_TABLE)
    print(f"Saved table '{OUTPUT_TABLE}' to {DB_PATH}")

    # # save also a simplified version of the geometry for faster loading later
    # gdf_jakarta["geometry"] = gdf_jakarta["geometry"].simplify(tolerance=0.0005,preserve_topology=True)
    # boundary_df = build_boundary_table(gdf_jakarta)
    # save_boundary_table(boundary_df, DB_PATH, OUTPUT_TABLE+'_simplified')

    print("\n=== SQLite preview ===")
    preview_saved_table(DB_PATH, OUTPUT_TABLE)
if __name__ == "__main__":
    main()
