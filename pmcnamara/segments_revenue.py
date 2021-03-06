import pandas as pd
import numpy as np
import sqlalchemy
import redshift_sqlalchemy
import glob
import os

# importing segment flags #
knicks = pd.read_excel('/Users/mcnamarp/Downloads/MSG Segmentation phase_20170418_Knicks.xlsx', sheetname = 'Knicks')[['uuid','Segment Knicks']]
rangers = pd.read_excel('/Users/mcnamarp/Downloads/MSG Segmentation phase_20170418_Rangers.xlsx', sheetname = 'Rangers')[['uuid','Segment Rangers']]

# creating labels #
segment_labels_knicks = pd.DataFrame(index = range(1,7), columns = ['segment'])
segment_labels_knicks['segment'] = ['Emo-Social','Purist','Root home','Competitor','Die-hards','Old Faithful']
segment_labels_rangers = pd.DataFrame(index = range(1,8), columns = ['segment'])
segment_labels_rangers['segment'] = ['Social Media','Scientist','Root home','Couch Potato','Live Game','Die-hards','Old Faithful']

# labeling survey respondents #
knicks = pd.merge(knicks, segment_labels_knicks, left_on = 'Segment Knicks', right_index = True).drop('Segment Knicks', axis = 1)
rangers = pd.merge(rangers, segment_labels_rangers, left_on = 'Segment Rangers', right_index = True).drop('Segment Rangers', axis = 1)
segments = knicks.append(rangers, ignore_index = True)

# combining survey response da ta #
sth = pd.read_excel('/Users/mcnamarp/Downloads/fac17002/STH/fac17002.xlsx', sheetname = 'A1')[['uuid','source','Sample']]
indy = pd.read_excel('/Users/mcnamarp/Downloads/fac17002/Individual_Game_Purchasers/fac17002.xlsx', sheetname = 'A1')[['uuid','source','Sample']]
#indy_test = pd.read_excel('/Users/mcnamarp/Downloads/fac17002_Indy_MH.xlsx', sheetname = 'A1')[['source','email']]
panel = pd.read_excel('/Users/mcnamarp/Downloads/fac17002/Panel/fac17002.xlsx', sheetname = 'A1')[['uuid','source','Sample']]
survey_data = sth.append(panel, ignore_index = True).append(indy, ignore_index = True)
survey_data.replace({'Sample':{1:'Panel',2:'STH',3:'Indy'}}, inplace = True)
survey_data = pd.merge(survey_data, segments, on = 'uuid', how = 'left')

# mapping respondents via Nat's files and combining #
path = '/Users/mcnamarp/Downloads/FW%3a_Survey_Lists'
all_files = glob.glob(os.path.join(path, "*.csv"))
df_from_each_file = (pd.read_csv(f, dtype = {'acct_id':'str'}) for f in all_files)
concatenated_df = pd.concat(df_from_each_file, ignore_index=True)
mapping = concatenated_df[['EMAIL','uid']].rename(columns = {'EMAIL':'email'}).dropna()
mapping['email'] = mapping['email'].str.lower()

engine = sqlalchemy.create_engine("redshift+psycopg2://mcnamarp:Welcome2859!@msgbiadb-prod.cqp6htpq4zp6.us-east-1.rds.amazonaws.com:5432/msgbiadb")
revenue_query = '''
SELECT email, description, regexp_replace(tm_season_name, '^.* ', '') AS team, cost::integer, tickets FROM (
SELECT lower(email_address) AS email, ticket_product_description AS description, SUM(CASE WHEN tm_price_code_desc = 'Madison Club' THEN 500 ELSE tickets_total_revenue END) AS cost, SUM(tickets_sold) AS tickets, tm_season_name
FROM ads_main.t_ticket_sales_event_seat A
WHERE tm_season_name IN ('2016-17 New York Knicks','2016-17 New York Rangers') AND tm_comp_code = '0' AND email_address IS NOT NULL
GROUP BY email_address, ticket_product_description, tm_season_name) A;
'''
tm_revenue = pd.read_sql(revenue_query, engine)
tm_revenue = tm_revenue[(tm_revenue['cost'] > 0) & (tm_revenue['tickets'] > 0)]

data = pd.merge(tm_revenue, mapping, on = 'email')
data = pd.merge(data, survey_data, left_on = 'uid', right_on = 'source').drop(['uid','source'], axis = 1).drop_duplicates()
data = data.append(tm_revenue.drop(['email'], axis = 1)).drop_duplicates()
data['avg_ticket'] = np.round(data['cost'] / data['tickets']).astype(int)
data['segment'].fillna('unknown', inplace = True)
data[['email','description','team','cost','tickets','segment','avg_ticket']].to_csv('tickets.csv', index = False)

knicks_all = tm_revenue[(tm_revenue['team'] == 'Knicks') & (tm_revenue['cost'] < 10000)]['cost']
stats.probplot(knicks_all, plot = pylab)
pylab.show()
rangers_all = tm_revenue[(tm_revenue['team'] == 'Rangers') & (tm_revenue['cost'] < 10000)]['cost']
stats.probplot(rangers_all, plot = pylab)
pylab.show()