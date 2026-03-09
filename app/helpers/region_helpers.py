import pandas as pd
from helpers.formatting import short_city_name

def available_map_times(df: pd.DataFrame) -> list[pd.Timestamp]:
    if df.empty:
        return []
    return sorted(pd.to_datetime(df["local_datetime"]).dropna().unique().tolist())


def infer_time_step(times: list[pd.Timestamp]):
    if len(times) < 2:
        return pd.Timedelta(hours=3)

    diffs = pd.Series(times).sort_values().diff().dropna()
    if diffs.empty:
        return pd.Timedelta(hours=3)

    return diffs.mode().iloc[0]


def nearest_available_time(selected_time, map_times: list[pd.Timestamp]):
    if not map_times:
        return None

    if selected_time is None:
        return pd.Timestamp(map_times[0])

    selected_time = pd.Timestamp(selected_time)
    return min(map_times, key=lambda t: abs(pd.Timestamp(t) - selected_time))

def nearest_available_time_in_df(df: pd.DataFrame, now=None):
    times = available_map_times(df)
    if not times:
        return None

    if now is None:
        # now = pd.Timestamp('2026-03-20 13:42:15.382917')
        now = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None)

    times = pd.to_datetime(pd.Series(times))
    nearest_idx = (times - now).abs().idxmin()
    return pd.Timestamp(times.loc[nearest_idx])

def forecast_at_selected_time(df: pd.DataFrame, selected_time) -> pd.DataFrame:
    if df.empty or selected_time is None:
        return df.iloc[0:0].copy()

    selected_time = pd.Timestamp(selected_time)
    out = df[df["local_datetime"] == selected_time].copy()

    return (
        out.sort_values(["kotkab", "kecamatan", "desa_kelurahan"])
        .reset_index(drop=True)
    )

def region_filter_options(
    df: pd.DataFrame,
    column: str,
    prior_mask: pd.Series | None = None,
) -> list[str]:
    subset = df if prior_mask is None else df[prior_mask]
    return sorted(
        subset[column]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

def city_summary_at_time(df: pd.DataFrame, selected_time) -> pd.DataFrame:
    if df.empty or selected_time is None:
        return pd.DataFrame()

    snap = df[df["local_datetime"] == pd.Timestamp(selected_time)].copy()
    if snap.empty:
        return pd.DataFrame()

    summary = (
        snap.groupby("kotkab", as_index=False)
        .agg(
            temperature_c=("temperature_c", "mean"),
            humidity_pct=("humidity_pct", "mean"),
            heat_index_c=("heat_index_c", "mean"),
        )
        .sort_values("kotkab")
        .reset_index(drop=True)
    )
    return summary

def get_fixed_city_order(forecast_df: pd.DataFrame) -> list[str]:
    if forecast_df.empty or "kotkab" not in forecast_df.columns:
        return []

    cities = (
        forecast_df["kotkab"]
        .dropna()
        .astype(str)
        .str.strip()
        .sort_values()
        .unique()
        .tolist()
    )
    return [short_city_name(city) for city in cities]