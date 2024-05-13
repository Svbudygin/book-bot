# import gspread
# import datetime
# import gspread_asyncio
# from utils import config

# gc = gspread.service_account(filename="service_account.json")
# sh = gc.open_by_key(config["sheet_id"])


# # def add_new_order(ISBN, title, destination, tg_id, tg_username) -> None:
# #     worksheet = sh.get_worksheet_by_id("1108347278")
# #     today = datetime.datetime.today()
# #     today = datetime.datetime.strftime(today, '%d/%m/%Y %H:%M:%S')
# #     client = find_user_by_name(tg_username, str(tg_id))[0]
# #     book = find_book(ISBN, title)
# #     if destination == "РФ":
# #         price_rf = book[2]
# #         price_es = ''
# #     else:
# #         price_rf = ''
# #         price_es = book[3]
# #     if client is None:
# #         client = 'NA'
# #     transaction = [title, '', client, 1, ISBN, book[1], price_rf, price_es, destination, tg_id,
# #                   tg_username, today]
# #     worksheet.append_row(transaction)
# def add_new_order(ISBN, title, destination, tg_id, tg_username) -> None:
#     tg_id = str(tg_id)
#     worksheet = sh.get_worksheet_by_id("1108347278")
#     today = datetime.datetime.today()
#     today = datetime.datetime.strftime(today, '%d/%m/%Y %H:%M:%S')
#     client = find_user_by_name(tg_username, tg_id)
#     book = find_book(ISBN, title)
#     if destination == "РФ":
#         price_rf = book[2]
#         price_es = ''
#     else:
#         price_rf = ''
#         price_es = book[3]
#     if client is None:
#         client = 'NA'
#     else:
#         client = client[0]
#     transaction = [title, '', client, 1, ISBN, book[1], price_rf, price_es, destination, tg_id,
#                   tg_username, today]
#     worksheet.append_row(transaction)

# def find_user_by_name(tg_username, tg_id):
#     worksheet = sh.get_worksheet_by_id("129882199")
#     res = worksheet.find(tg_username, in_column=2)
#     try:
#         res = worksheet.row_values(res.row)
#     except gspread.exceptions.APIError:
#         pass
#     except AttributeError:
#         pass
#     if res is None:
#         res = worksheet.find(tg_id, in_column=3)
#         try:
#             res = worksheet.row_values(res.row)
#         except gspread.exceptions.APIError:
#             pass
#         except AttributeError:
#             pass
#     return res



# def find_book(isbn: str, title_of_list: str):
#     id_of_list = sh.worksheet(title_of_list).id
#     name_book = None
#     worksheet = sh.get_worksheet_by_id(id_of_list)
#     res = worksheet.find(isbn, in_column=1)
#     if res is not None:
#         res = worksheet.row_values(res.row)
#         name_book = worksheet.title
#     return res + [name_book]


# def remove_order(user_id, isbn):
#     print(user_id) 
#     user_id = str(user_id) if user_id else user_id
#     worksheet = sh.get_worksheet_by_id('1108347278')
#     res = worksheet.find(user_id, in_column=10)
#     value = worksheet.row_values(res.row)
#     if value[4] == isbn:
#         worksheet.delete_rows(res.row)


# if __name__ == "__main__":
#     remove_order("1995264099", "")
import gspread
import datetime
import gspread_asyncio
from utils import config

gc = gspread.service_account(filename="service_account.json")
sh = gc.open_by_key(config["sheet_id"])


def add_new_order(ISBN, title, destination, tg_id, tg_username) -> None:
    tg_id = str(tg_id)
    worksheet = sh.get_worksheet_by_id("1108347278")
    today = datetime.datetime.today()
    today = datetime.datetime.strftime(today, '%d/%m/%Y %H:%M:%S')
    client = find_user_by_name(tg_username, tg_id, destination)
    book = find_book(ISBN, title)
    if destination == "РФ":
        price_rf = book[2]
        price_es = ''
    else:
        price_rf = ''
        price_es = book[3]
    if client is None:
        client = 'NA'
    transaction = [title, book[0], client, 1, ISBN, book[1], price_rf, price_es, destination, tg_id,
                   tg_username, today]
    worksheet.append_row(transaction)


def find_user_by_name(tg_username, tg_id, region):
    worksheet = sh.get_worksheet_by_id("129882199")
    res = worksheet.findall(tg_username, in_column=2)
    ret = None
    for e in res:
        value = worksheet.row_values(e.row)
        if len(value) == 2:
            ret = value[0]
        elif len(value) == 4:
            if value[3] == region:
                ret = value[0]
                break
    if ret is None:
        res = worksheet.findall(tg_id, in_column=3)
        for e in res:
            value = worksheet.row_values(e.row)
            if len(value) == 3:
                ret = value[0]
            elif len(value) == 4:
                if value[3] == region:
                    ret = value[0]
                    break
    return ret


def find_book(isbn: str, title_of_list: str):
    id_of_list = sh.worksheet(title_of_list).id
    name_book = None
    worksheet = sh.get_worksheet_by_id(id_of_list)
    res = worksheet.find(isbn, in_column=5)
    if res is not None:
        res = worksheet.row_values(res.row)
        name_book = worksheet.title
    return res + [name_book]


def get_storka(isbn: str, title_of_list: str):
    print(isbn,title_of_list )
    id_of_list = sh.worksheet(title_of_list).id
    worksheet = sh.get_worksheet_by_id(id_of_list)
    res = worksheet.find(isbn, in_column=5)
    if res is not None:
        res = worksheet.row_values(res.row)[0]
    return res


def remove_order(user_id: str, isbn: str, region: str) -> None:
    worksheet = sh.get_worksheet_by_id('1108347278')
    res = worksheet.findall(user_id, in_column=10)
    if res:
        res.reverse()
        for e in res:
            value = worksheet.row_values(e.row)
            if value[4] == isbn and value[8] == region:
                worksheet.delete_rows(e.row)
                break


if __name__ == "__main__":
    print(find_user_by_name('Кф', '255552517', 'ЕС'))