from pathlib import Path
from streamlit.testing.v1 import AppTest
import pytest

APP = Path(__file__).resolve().parents[1] / 'app.py'


@pytest.fixture(scope='module')
def app():
    return AppTest.from_file(str(APP), default_timeout=90).run()


@pytest.mark.parametrize('page', ['Overview', 'Products', 'Forecast', 'Pricing', 'Experiment', 'Analyst', 'Methodology'])
def test_pages_render_without_exception(app, page):
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception
    assert len(app.title) == 1


def test_pricing_controls_update_profit(app):
    app.sidebar.radio[0].set_value('Pricing').run()
    baseline = app.metric[0].value
    app.slider[0].set_value(10).run()
    assert not app.exception
    assert app.metric[0].value != baseline


def test_analyst_executes_question(app):
    app.sidebar.radio[0].set_value('Analyst').run()
    app.text_area[0].set_value('Why did profitability fall in 2011-01?')
    app.button[0].click().run()
    assert not app.exception
    assert any('decreased' in x.value for x in app.markdown)
