from app.components import theme


def test_native_kpi_cards_have_a_fixed_height_and_label_reserve(monkeypatch):
    rendered = []
    monkeypatch.setattr(theme.st, "markdown", lambda body, **kwargs: rendered.append(body))

    theme.inject_css()

    css = rendered[0]
    native_metric_css = css.split('[data-testid="stMetric"]', maxsplit=1)[1]
    assert "min-height: 112px" in native_metric_css
    assert "justify-content: space-between" in native_metric_css
    assert '[data-testid="stMetricLabel"]' in css
    assert "min-height: 2.5rem" in css


def test_dashboard_cards_and_charts_have_light_borders(monkeypatch):
    rendered = []
    monkeypatch.setattr(theme.st, "markdown", lambda body, **kwargs: rendered.append(body))

    theme.inject_css()

    css = rendered[0]
    assert '[data-testid="stPlotlyChart"]' in css
    assert '[data-testid="stDataFrame"]' in css
    assert "border: 1px solid #E5E7EB" in css


def test_collapsed_sidebar_releases_the_full_dashboard_width(monkeypatch):
    rendered = []
    monkeypatch.setattr(theme.st, "markdown", lambda body, **kwargs: rendered.append(body))

    theme.inject_css()

    css = rendered[0]
    assert '[data-testid="stSidebar"][aria-expanded="false"]' in css
    assert "max-width: none !important" in css
