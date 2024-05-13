import asyncio
import gspread_asyncio
from google.oauth2.service_account import Credentials
from utils import config
import gspread
import datetime
import gspread_asyncio
from utils import config


class Record:
    @staticmethod
    def get_credentials() -> Credentials:
        return Credentials.from_service_account_file("service_account.json").with_scopes(
            [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )

    client_manager = gspread_asyncio.AsyncioGspreadClientManager(get_credentials)

    def __init__(
        self,
        isbn: str,
        title: str,
        price_rub: int | float,
        price_eur: int | float,
        description: str,
        hashtag: str,
        target_age: str,
        pictures: list[str]) -> None:
        self.isbn: str = isbn
        self.title: str = title
        self.price_rub: int | float = price_rub
        self.price_eur: int | float = price_eur
        self.description: str = description
        self.hashtag: str = hashtag
        self.target_age: str = target_age
        self.pictures: list[str] = pictures

    def __str__(self) -> str:
        result: str = ""
        for attr, value in vars(self).items():
            result += attr + ": " + str(value) + "\n"
        return result

    @classmethod
    async def from_gspread(cls, worksheet_title: str, page=1) -> list:
        gs = await Record.client_manager.authorize()
        table = await gs.open_by_key(config["sheet_id"])
        worksheet = await table.worksheet(worksheet_title)
        records: list[dict] = await worksheet.get_all_records(value_render_option="UNFORMATTED_VALUE")
        result: list[cls] = []
        print("len =", len(records))
        for record in records[int(page)-2:]:
            obj = cls(
                isbn=str(record["ISBN"]),
                title=str(record["Название"]),
                price_rub=record["Цена руб"],
                price_eur=record["Цена евро"],
                description=str(record["Описание"]),
                hashtag="",
                target_age=str(record["Название"]),
                pictures=[
                    link for link in (
                        record["Ссылка на картинку 1"],
                        record["Ссылка на картинку 2"],
                        record["Ссылка на картинку 3"],
                        record["Ссылка на картинку 4"],
                        record["Ссылка на картинку 5"]
                    ) if link
                ]
            )
            result.append(obj)
        return result