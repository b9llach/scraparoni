from scraparoni import Scraparoni as scrapey
from pydantic import BaseModel, Field
from typing import Optional, List

class NavbarItems(BaseModel):
    navbar_items: List[str] = Field(description="The navbar items")

scrapey = scrapey()
result = scrapey.scrape(
    url="https://www.scrapethissite.com/",
    schema=NavbarItems,
    use_browser=False,
    instructions="Give me the names of the items in the navbar"
)

print(result.json())