from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
GIFS_DIR = ROOT / "gifs"
PERIODS = ("2012-2014", "2015-2017", "2018-2020", "2021-2023", "2024-2026")
SELECTED_COUNTRIES = {"Bolivia", "Colombia", "Guatemala", "Honduras", "Paraguay"}
SELECTED_CAPITALS = {
    "bolivia_la_paz",
    "colombia_bogota",
    "guatemala_ciudad_de_guatemala",
    "honduras_tegucigalpa",
    "paraguay_asuncion",
}
SERIES = (
    ("Ciudades capitales", "capitales", "#2563A6", "o"),
    ("Húmedo Sur", "humedo_sur", "#16856B", "s"),
    ("Húmedo Norte", "humedo_norte", "#7A5195", "^"),
    ("Seco", "seco", "#C65D21", "D"),
)
DEFAULT_OUTPUT = GIFS_DIR / "evolucion_agregada_vegetacion_clases_trienios_2012.gif"
DEFAULT_CSV = DATA_DIR / "agregado_vegetacion_clases_trienios_2012.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def aggregate_values() -> dict[str, list[float]]:
    capital_rows = read_csv(DATA_DIR / "capitales_seleccionadas_trienios_2012_2026_1000km2.csv")
    biome_rows = read_csv(DATA_DIR / "estadisticas_grupo_a_trienios_2012.csv")

    values = {key: [] for _, key, _, _ in SERIES}
    for period in PERIODS:
        capital_total = sum(
            float(row["area_bosque_probable_km2"])
            for row in capital_rows
            if row["slug"] in SELECTED_CAPITALS and row["epoca"] == period
        )
        values["capitales"].append(capital_total)

        selected = [
            row
            for row in biome_rows
            if row["pais"] in SELECTED_COUNTRIES and row["epoca"] == period
        ]
        for biome, key in (("HUMEDO_SUR", "humedo_sur"), ("HUMEDO_NORTE", "humedo_norte"), ("SECO", "seco")):
            values[key].append(sum(float(row["area_bosque_km2"]) for row in selected if row["bioma"] == biome))

    expected = len(PERIODS)
    if any(len(items) != expected for items in values.values()):
        raise RuntimeError("No fue posible construir todas las series agregadas.")
    return values


def write_aggregate_csv(path: Path, values: dict[str, list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("epoca", "ciudades_capitales_km2", "humedo_sur_km2", "humedo_norte_km2", "seco_km2"))
        for index, period in enumerate(PERIODS):
            writer.writerow(
                (
                    period,
                    f"{values['capitales'][index]:.4f}",
                    f"{values['humedo_sur'][index]:.4f}",
                    f"{values['humedo_norte'][index]:.4f}",
                    f"{values['seco'][index]:.4f}",
                )
            )


def render_frame(values: dict[str, list[float]], current_index: int) -> Image.Image:
    background = "#F5F7F8"
    foreground = "#172026"
    muted = "#5E6A71"
    grid = "#D8DEE2"
    x = list(range(len(PERIODS)))

    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=background)
    layout = fig.add_gridspec(1, 2, width_ratios=(3.25, 1.15), left=0.07, right=0.96, top=0.80, bottom=0.13, wspace=0.20)
    trend = fig.add_subplot(layout[0, 0])
    snapshot = fig.add_subplot(layout[0, 1])

    fig.text(0.07, 0.93, "Evolución agregada de vegetación densa", color=foreground, fontsize=28, fontweight="bold")
    fig.text(0.07, 0.875, "Cinco capitales y cinco frentes agrupados por tipo de bioma · km²", color=muted, fontsize=16)
    fig.text(0.96, 0.93, PERIODS[current_index], color=foreground, fontsize=24, fontweight="bold", ha="right")

    trend.set_facecolor("#FFFFFF")
    trend.set_xlim(-0.12, len(PERIODS) - 0.72)
    trend.set_ylim(0, 2000)
    trend.set_xticks(x, PERIODS)
    trend.set_yticks(range(0, 2001, 250))
    trend.set_ylabel("Vegetación densa agregada (km²)", color=foreground, fontsize=13)
    trend.grid(axis="y", color=grid, linewidth=1)
    trend.tick_params(axis="both", colors=muted, labelsize=11)
    trend.spines[["top", "right", "left"]].set_visible(False)
    trend.spines["bottom"].set_color(grid)
    trend.axvline(current_index, color="#9AA5AB", linewidth=1.2, linestyle=(0, (3, 4)), zorder=1)

    for label, key, color, marker in SERIES:
        current_x = x[: current_index + 1]
        current_y = values[key][: current_index + 1]
        trend.plot(current_x, current_y, color=color, linewidth=3.4, marker=marker, markersize=9, label=label, zorder=3)
        trend.scatter([current_index], [current_y[-1]], s=150, color=color, edgecolor="#FFFFFF", linewidth=2.2, zorder=4)

    trend.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.10),
        ncol=4,
        frameon=False,
        fontsize=12,
        handlelength=2.2,
    )

    labels = [label for label, _, _, _ in SERIES]
    current_values = [values[key][current_index] for _, key, _, _ in SERIES]
    colors = [color for _, _, color, _ in SERIES]
    y_positions = list(range(len(SERIES)))[::-1]
    snapshot.set_facecolor("#FFFFFF")
    snapshot.barh(y_positions, current_values, color=colors, height=0.56)
    snapshot.set_yticks(y_positions, labels)
    snapshot.set_xlim(0, 2000)
    snapshot.set_xticks(range(0, 2001, 500))
    snapshot.set_title("Valor en el período", color=foreground, fontsize=16, fontweight="bold", pad=18)
    snapshot.grid(axis="x", color=grid, linewidth=1)
    snapshot.set_axisbelow(True)
    snapshot.tick_params(axis="x", colors=muted, labelsize=10)
    snapshot.tick_params(axis="y", colors=foreground, labelsize=11, length=0)
    snapshot.spines[["top", "right", "left"]].set_visible(False)
    snapshot.spines["bottom"].set_color(grid)
    for y_position, value in zip(y_positions, current_values):
        snapshot.text(value + 28, y_position, f"{value:,.1f}", va="center", color=foreground, fontsize=12, fontweight="bold")

    fig.text(
        0.07,
        0.055,
        "Capitales: La Paz, Bogotá, Ciudad de Guatemala, Tegucigalpa y Asunción  |  "
        "Húmedo Sur: Colombia  |  Húmedo Norte: Guatemala + Honduras  |  Seco: Bolivia + Paraguay",
        color=muted,
        fontsize=11,
    )

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=100, facecolor=background)
    plt.close(fig)
    buffer.seek(0)
    frame = Image.open(buffer).convert("RGB").copy()
    buffer.close()
    return frame


def make_gif(output_path: Path, values: dict[str, list[float]]) -> None:
    frames = [render_frame(values, index) for index in range(len(PERIODS))]
    palette_frames = [frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=192) for frame in frames]
    durations = [1400] * len(palette_frames)
    durations[-1] = 2800
    output_path.parent.mkdir(parents=True, exist_ok=True)
    palette_frames[0].save(
        output_path,
        save_all=True,
        append_images=palette_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"GIF agregado -> {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera la evolución agregada de capitales y tipos de bioma.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--csv-output", type=Path, default=DEFAULT_CSV)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    aggregated = aggregate_values()
    write_aggregate_csv(args.csv_output, aggregated)
    make_gif(args.output, aggregated)
