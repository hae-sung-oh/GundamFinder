from dataclasses import dataclass

@dataclass(frozen=True)
class Store:
    id: int
    name : str
    region: str
