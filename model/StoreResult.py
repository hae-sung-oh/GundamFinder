from dataclasses import dataclass

from model.Store import Store
from model.SearchItem import SearchItem


@dataclass(frozen=True)
class StoreResult:
    store : Store
    search_items : list[SearchItem]