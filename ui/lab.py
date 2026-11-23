"""Apresentação dos dados experimentais em telas largas e estreitas."""
from html import escape

import altair as alt
import pandas as pd
import streamlit as st


def render_table(data):
    st.dataframe(data, hide_index=True)
    cards = []
    for row in data.itertuples(index=False, name=None):
        fields = []
        for column, value in zip(data.columns, row):
            display = "—" if pd.isna(value) else str(value)
            if isinstance(value, float):
                display = display.replace(".", ",")
            fields.append(f"<div><dt>{escape(column)}</dt><dd>{escape(display)}</dd></div>")
        cards.append(f"<li><dl>{''.join(fields)}</dl></li>")
    st.markdown(
        f'<ul class="lab-table-cards" aria-label="Dados do experimento">{"".join(cards)}</ul>',
        unsafe_allow_html=True,
    )


def _render_chart(data, x, y, *, kind, series=None):
    x_axis = alt.X(field=x, type="quantitative", axis=alt.Axis(tickCount=5))
    y_axis = alt.Y(field=y, type="quantitative", axis=alt.Axis(tickCount=5))
    tooltip = [alt.Tooltip(field=field, type="quantitative") for field in (x, y)]
    chart = alt.Chart(data).mark_line(strokeWidth=2.5) if kind == "line" else alt.Chart(data).mark_circle(size=55)
    if series:
        chart = chart.encode(color=alt.Color(
            field=series, type="nominal",
            legend=alt.Legend(orient="bottom", columns=1, labelLimit=210, title=None),
        ))
        tooltip.insert(0, alt.Tooltip(field=series, type="nominal"))
    else:
        chart = chart.encode(color=alt.value("#11685e"))
    height = 340 if series else 250
    chart = chart.encode(x=x_axis, y=y_axis, tooltip=tooltip).properties(height=height)
    st.altair_chart(chart, width="stretch")


def render_line(data, y=None):
    x = "Tempo (s)" if data.index.name == "t (s)" else data.index.name
    frame = data.rename_axis(x).reset_index()
    if len(data.columns) == 1:
        _render_chart(frame, x, data.columns[0], kind="line")
    else:
        frame = frame.melt(id_vars=x, var_name="Cenário", value_name=y)
        _render_chart(frame, x, y, kind="line", series="Cenário")


def render_scatter(data):
    _render_chart(
        data.rename(columns={"Temp. estabilizada (°C)": "Temperatura (°C)"}),
        "Potência (W)", "Temperatura (°C)", kind="point", series="Série",
    )
