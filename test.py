from pydantic import BaseModel, Field
from scraparoni import Scraparoni

class Story(BaseModel):
    title: str = Field(description="Story title")
    points: int = Field(description="Story points")

scraper = Scraparoni()

result = scraper.scrape_with_phantom(
    url="https://news.ycombinator.com",
    schema=Story,
    instructions="Extract the top story"
)

print(result.json())