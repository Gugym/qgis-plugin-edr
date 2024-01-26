import json

import sip
from qgis.core import QgsDataCollectionItem, QgsDataItem, QgsDataItemProvider, QgsDataProvider, QgsSettings
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from edr_plugin.utils import icon_filepath


class EdrRootItem(QgsDataCollectionItem):
    """EDR root data containing server groups item with saved queries."""

    def __init__(
        self,
        plugin,
        name=None,
        parent=None,
    ):
        name = plugin.PLUGIN_NAME if not name else name
        provider_key = plugin.PLUGIN_ENTRY_NAME
        QgsDataCollectionItem.__init__(self, parent, name, provider_key)
        self.plugin = plugin
        self.setIcon(QIcon(icon_filepath("edr.png")))
        self.server_items = []
        self.base_name = self.name()

    def createChildren(self):
        settings = QgsSettings()
        available_servers = settings.value("edr_plugin/server_urls", [])
        items = []
        for server_url in available_servers:
            server_item = EdrServerItem(self.plugin, server_url, self)
            server_item.setState(QgsDataItem.Populated)
            server_item.refresh()
            sip.transferto(server_item, self)
            items.append(server_item)
            self.server_items.append(server_item)
        return items

    def refresh_saved_queries(self):
        for item in self.server_items:
            item.refresh()

    def actions(self, parent):
        actions = []
        action_run = QAction(QIcon(icon_filepath("play.png")), "Run query", parent)
        action_run.triggered.connect(self.plugin.run)
        actions.append(action_run)
        action_refresh = QAction(QIcon(icon_filepath("reload.png")), "Refresh", parent)
        action_refresh.triggered.connect(self.refresh_saved_queries)
        actions.append(action_refresh)
        return actions


class EdrServerItem(EdrRootItem):
    """EDR group data item. Contains saved queries."""

    def __init__(self, plugin, server_url, parent):
        EdrRootItem.__init__(self, plugin, server_url, parent)
        self.plugin = plugin
        self.server_url = server_url
        self.setIcon(QIcon(icon_filepath("server.png")))

    def createChildren(self):
        settings = QgsSettings()
        saved_queries = json.loads(settings.value("edr_plugin/saved_queries", "{}"))
        queries = saved_queries.get(self.server_url, {})
        items = []
        for query_name in queries.keys():
            query_item = SavedQueryItem(self.plugin, self.server_url, query_name, self)
            query_item.setState(QgsDataItem.Populated)
            query_item.refresh()
            sip.transferto(query_item, self)
            items.append(query_item)
        return items


class SavedQueryItem(QgsDataItem):
    def __init__(self, plugin, server_url, query_name, parent):
        self.plugin = plugin
        self.server_url = server_url
        self.query_name = query_name
        QgsDataItem.__init__(self, QgsDataItem.Collection, parent, query_name, f"/{server_url}/{query_name}")
        self.setIcon(QIcon(icon_filepath("request.png")))

    def replay_query(self):
        self.plugin.ensure_main_dialog_initialized()
        self.plugin.main_dialog.query_data_collection()

    def delete_query(self):
        settings = QgsSettings()
        saved_queries = json.loads(settings.value("edr_plugin/saved_queries", "{}"))
        del saved_queries[self.server_url][self.query_name]
        settings.setValue("edr_plugin/saved_queries", json.dumps(saved_queries))
        self.parent().refresh()

    def actions(self, parent):
        action_rerun = QAction(QIcon(icon_filepath("replay.png")), "Replay query", parent)
        action_rerun.triggered.connect(self.replay_query)
        action_delete = QAction(QIcon(icon_filepath("delete.png")), "Delete", parent)
        action_delete.triggered.connect(self.delete_query)
        actions = [action_rerun, action_delete]
        return actions


class SavedQueriesItemProvider(QgsDataItemProvider):
    def __init__(self, plugin):
        QgsDataItemProvider.__init__(self)
        self.root_item = None
        self.plugin = plugin

    def name(self):
        return "EdrProvider"

    def capabilities(self):
        return QgsDataProvider.Net

    def createDataItem(self, path, parentItem):
        if not parentItem:
            ri = EdrRootItem(plugin=self.plugin)
            sip.transferto(ri, None)
            self.root_item = ri
            return ri
        else:
            return None
