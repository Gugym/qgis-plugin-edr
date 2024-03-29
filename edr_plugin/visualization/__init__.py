import os

from qgis.core import QgsMeshLayer, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.utils import iface

from edr_plugin.coveragejson.coverage_json_reader import CoverageJSONReader
from edr_plugin.utils import add_to_layer_group, single_band_gray_renderer, spawn_layer_group


class EdrLayerException(Exception):
    pass


class EdrLayerManager:
    def __init__(self, plugin):
        self.plugin = plugin
        self.project = QgsProject.instance()
        self.loaded_layers = {}

    def add_layers(self, *layers, group=None):
        if group is None:
            for layer in layers:
                self.project.addMapLayer(layer)
                self.loaded_layers[layer.id()] = layer
        else:
            for layer in layers:
                add_to_layer_group(self.project, group, layer)
                self.loaded_layers[layer.id()] = layer

    def ogr_layer_loader(self, filepath, layer_name):
        layer = QgsVectorLayer(filepath, layer_name, "ogr")
        self.add_layers(layer)

    def gdal_layer_loader(self, filepath, layer_name):
        layer = QgsRasterLayer(filepath, layer_name, "gdal")
        single_band_gray_renderer(layer)
        self.add_layers(layer)

    def mdal_layer_loader(self, filepath, layer_name):
        layer = QgsMeshLayer(filepath, layer_name, "mdal")
        self.add_layers(layer)

    def covjson_layer_loader(self, filepath, layer_name):
        try:
            self.plugin.communication.progress_bar(f"Parsing '{filepath}' CoverageJSON ...", clear_msg_bar=True)
            covjson_reader = CoverageJSONReader(filepath)
            if covjson_reader.coverages_count > 1000 and covjson_reader.file_size_mg > 10:
                msg = f"The CoverageJSON file is either large in size or contains a lot of coverages. It may take a long time to load. The file is located at `{filepath}`.\nDo you want to continue?"
                load = self.plugin.communication.ask(self.plugin.iface.mainWindow(), "Load large CoverageJSON", msg)
                if not load:
                    self.plugin.communication.clear_message_bar()
                    self.plugin.communication.bar_info("File not loaded.")
                    return
        except ValueError as e:
            self.plugin.communication.clear_message_bar()
            error_msg = f"Can't load CoverageJSON: '{e}'."
            raise EdrLayerException(error_msg)
        layers = covjson_reader.map_layers()
        self.plugin.communication.clear_message_bar()
        self.plugin.communication.bar_info("CoverageJSON parsed successfully.")
        layers_group = spawn_layer_group(self.project, layer_name)
        self.add_layers(*layers, group=layers_group)
        covjson_reader.qgsproject_setup_time_settings()

    @property
    def file_extension_layer_loaders(self):
        extension_to_loader_map = {
            ".covjson": self.covjson_layer_loader,
            ".geojson": self.ogr_layer_loader,
            ".gpkg": self.ogr_layer_loader,
            ".grib2": self.mdal_layer_loader,
            ".json": self.ogr_layer_loader,
            ".kml": self.ogr_layer_loader,
            ".nc": self.mdal_layer_loader,
            ".tif": self.gdal_layer_loader,
            ".tiff": self.gdal_layer_loader,
            ".geotiff": self.gdal_layer_loader,
        }
        return extension_to_loader_map

    def add_layer_from_file(self, filepath, layer_name=None):
        no_extension_filepath, file_extension = os.path.splitext(filepath)
        file_extension = file_extension.lower()
        try:
            layer_loader = self.file_extension_layer_loaders[file_extension]
            if layer_name is None:
                layer_name = os.path.basename(filepath)
            layer_loader(filepath, layer_name)
        except KeyError:
            self.plugin.communication.bar_warn(f"Can't load file as a layer - unsupported format: '{file_extension}'.")
            return False
        except EdrLayerException as e:
            self.plugin.communication.bar_warn(f"{e}")
            return False
        except Exception as e:
            self.plugin.communication.bar_warn(f"Loading of '{filepath}' failed due to the following exception: {e}")
            return False
        return True
