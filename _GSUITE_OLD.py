# # Spreadsheet access
# import gspread
# from google.oauth2.service_account import Credentials
# 
# # # G Suite inits -- will be reused by sync process, which will likely be a separate lambda.
# gcreds = Credentials.from_service_account_file('config/creds.json', scopes=G_SCOPES)
# gc = gspread.authorize(gcreds)
# sheet = gc.open_by_key(SHEET_ID)

# signup = sheet.worksheet("Sign-Up Data")
# attendance = sheet.worksheet("Attendance")

# # Don't forget to update me often!
# signup_data = signup.get_values()
# attendance_data = attendance.get_values()

# # Returns location of user ID, or -1 if none.
# def id_to_row(user_id, sheet="signup"):
#     data = None
#     if sheet == "signup":
#         data = signup_data
#     elif sheet == "attendance":
#         data = attendance_data
#     else:
#         return -1

#     row_number = 0
#     for row in data:
#         if row[0] == str(user_id):
#             return (row_number + 1)
#         row_number += 1

#     return -1

# # Returns UUID of a Discord user, if possible.
# def snowflake_to_uuid(snowflake):
#     row_number = 0
#     for row in signup_data:
#         if row[1] == str(snowflake):
#             return row[0]
#         row_number += 1

#     return None

# def fetch_signup(user_id, column):
#     user_location = id_to_row(user_id, "signup")
#     if user_location == -1:
#         return None
#     number = gspread.utils.a1_to_rowcol(f"{column}{user_location}")
#     return signup_data[number[0] - 1][number[1] - 1]

# def fetch_attendance(user_id, column):
#     user_location = id_to_row(user_id, "attendance")
#     if user_location == -1:
#         return None
#     number = gspread.utils.a1_to_rowcol(f"{column}{user_location}")
#     return attendance_data[number[0] - 1][number[1] - 1]

# def set_signup(user_id, column, value):
#     user_location = id_to_row(user_id, "signup")
#     if user_location == -1:
#         return None
#     number = gspread.utils.a1_to_rowcol(f"{column}{user_location}")
#     signup_data[number[0] - 1][number[1] - 1] = value

# def refresh_user_from_memory_signup(user_id):
#     user_location = id_to_row(user_id, "signup")
#     if user_location == -1:
#         return False

#     memory_row = signup_data[user_location - 1]

#     signup.update(f"A{user_location}:ZZ{user_location}", [memory_row])

# def new_user_signup(user_id):
#     desired_len = len(signup_data[0])
#     data = []
#     for i in range(0, desired_len):
#         data.append("")

#     data[0] = user_id

#     signup_data.append(data)

"""
Because Google Docs has shitty rate limits, we are going to cache things in memory.
It's ugly, but it's that or SQL. Your pick.

fetch_signup("1", "B")  # For user ID "1", get the value of column B.
set_signup("1", "C", "owo")  # For user ID "1", set column C to "owo"
refresh_user_from_memory_signup("1")  # Push buffer for user "1" to G Suite.

"""