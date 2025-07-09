from dataclasses import dataclass

@dataclass
class SearchItem:
    name : str
    price : str
    stock : str

    def to_display_string(self):
        return f"{self.name}, {self.price}원, 재고: {self.stock}개"
