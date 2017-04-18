
from ...context import ModelCatalogContext


def before_all(context):
    context.zen_context = ModelCatalogContext()
