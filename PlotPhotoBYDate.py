import pandas as pd
import matplotlib.pyplot as plt
from datetime import date

df = pd.read_csv("E:/foss_backup/backup.status.csv", sep='|', header=0,  encoding="ISO-8859-1" )
print(df.columns)

df_after_2000 = df[df['year'] >= 2000]

df_year_month= df_after_2000.groupby(['year'])['row_id'].count()
df_year_month.plot(x = 'Year-Month', y = 'Files Count' , title='Number of photos and videos created by Year as of : ' + str(date.today()), markersize='10', marker = '.')
#df_year_month.plot(x = 'Run Id', y = 'Count' , title='Number of photos and videos created by year, as of {}'.format(date.today()), markersize='10', marker = '.')
#df_after_2000_after_first_run = df_after_2000[df_after_2000['run_id'] > 1593743 ]

#df_run_id = df_after_2000_after_first_run.groupby(['run_id'])['row_id'].count()
# df_run_id.plot(x = 'Run Id', y = 'Count' , title='Number of photos and videos created by Run Id  : ' + str(date.today()), markersize='10', marker = '.')

plt.show()

print(df.run_id.unique())
#
# plt.subplot(1, 2, 1) # row 1, col 2 index 1

# plt.plot(xPoints, y1Points)
# plt.title("My first plot!")
# plt.xlabel('X-axis ')
# plt.ylabel('Y-axis ')
#
# plt.subplot(1, 2, 2) # index 2
# plt.plot(xPoints, y2Points)
# plt.title("My second plot!")
# plt.xlabel('X-axis ')
# plt.ylabel('Y-axis ')
#
# plt.show()