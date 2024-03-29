import typing

from qgis.core import Qgis, QgsCategorizedSymbolRenderer, QgsMapLayer, QgsVectorLayer, QgsWkbTypes

from edr_plugin.coveragejson.coverage import Coverage
from edr_plugin.coveragejson.coverage_json_reader import CoverageJSONReader
from edr_plugin.coveragejson.utils import prepare_vector_render


def test_trajectory(data_dir):
    filename = data_dir / "coveragecollection_vector_trajectory.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)

    assert coverage_json.domain_type is None
    assert coverage_json.coverages_count == 221

    coverage = coverage_json.coverage()
    assert isinstance(coverage, Coverage)
    assert coverage.domain_type == "Trajectory"

    assert coverage.has_t is False
    assert coverage.has_z is False
    assert coverage.has_composite_axe is True

    assert coverage.parameter_names == ["Road_Type"]

    for param in coverage.parameter_names:
        assert coverage.parameter_ranges(param)
        assert isinstance(coverage.parameter_ranges(param), typing.Dict)

    layers = coverage.vector_layers()

    assert isinstance(layers, typing.List)
    assert len(layers) == 1
    assert isinstance(layers[0], QgsVectorLayer)
    assert layers[0].fields().count() == 1
    assert layers[0].dataProvider().featureCount() == 1
    assert layers[0].crs().authid() == "EPSG:4326"
    assert layers[0].wkbType() == Qgis.WkbType.LineString

    layers = coverage_json.map_layers()

    assert isinstance(layers, typing.List)
    assert len(layers) == 1
    assert isinstance(layers[0], QgsVectorLayer)
    assert layers[0].dataProvider().featureCount() == 221


def test_create_renderer(data_dir):
    filename = data_dir / "coveragecollection_vector_trajectory.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)

    coverage = coverage_json.coverage()
    assert isinstance(coverage, Coverage)

    layer = coverage.vector_layers()[0]
    assert layer.isValid()

    # only existing categories
    renderer = prepare_vector_render(layer, coverage.parameters, False)

    assert isinstance(renderer, QgsCategorizedSymbolRenderer)
    assert len(renderer.categories()) == 24

    # +1 category for no value
    renderer = prepare_vector_render(layer, coverage.parameters)

    assert isinstance(renderer, QgsCategorizedSymbolRenderer)
    assert len(renderer.categories()) == 25
