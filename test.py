from pydantic import BaseModel, Field
from typing import List
from scraparoni import Scraparoni

class Item(BaseModel):
    name: str = Field(description="The name of the item")
    url: str = Field(description="The full url of the item")

class NavbarItems(BaseModel):
    navbar_items: List[Item] = Field(description="The navbar items")
    
scraper = Scraparoni()

result = scraper.scrape(
    url="https://www.scrapethissite.com/",
    schema=NavbarItems,
    use_browser=False,
    instructions="Get the names and full urls of the items in the navbar"
)

print(result.json())