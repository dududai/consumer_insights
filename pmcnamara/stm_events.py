import pandas as pd
import sqlalchemy
import redshift_sqlalchemy
import statsmodels.api as sm
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import scale

# IMPORT RANGERS RSVPs #
nyr_fan_forum = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/Rangers Fan Forum Mail Merge 0109.xlsx', sheetname = 'temp')[['acct_id','email_addr','tag','acct_type']]
nyr_kids_camp = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/NYR Kids Training Camp STM List 1110 v2.xlsx', sheetname = 'temp')[['acct_id','email_addr','tag','acct_type']]
nyr_11_25_ = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/RANGERS - 2016-17 90th Year Communication (11 to 25 Year Subs) 11.12.16.....xlsx', sheetname = 'temp')[['acct_id','email_addr','tag','acct_type']]
nyr_viewing = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/Viewing Party Invite List.xlsx', sheetname = 'temp')[['acct_id','email_addr','tag','acct_type']]
nyr_ob = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/Rangers Tenure Events - ALL OB and LEG 1_24_17.xlsx', sheetname = 'temp')[['acct_id','email_addr','tag','acct_type']]
nyr_vet = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/Rangers Veteran Tenure Event Invite MM.xlsx', sheetname = 'Sheet1')[['acct_id','email_addr','tag','acct_type']]
nyr_half = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/1617 NYR Half Plan Viewing Parties.xlsx', sheetname = 'temp')[['acct_id','email_addr','tag','acct_type']]
nyr_rookie = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/Mail Merge NYR Rookie Accts 0110.xlsx', sheetname = 'temp')[['acct_id','email_addr','tag','acct_type']]
rangers_events = [nyr_fan_forum, nyr_kids_camp, nyr_11_25_, nyr_viewing, nyr_ob, nyr_vet, nyr_half, nyr_rookie]

# IMPORT KNICKS RSVPs #
nyk_11_25_ = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/KNICKS - 11 to 25 Year Tenure (mail merge) 12.20.16.xlsx', sheetname = 'temp')[['acct_id','email_addr','tag','acct_type']]
nyk_leg = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/Legends Knicks Tenure Event 3_1_17.xlsx', sheetname = 'Sheet1')[['acct_id','email_addr','tag','acct_type']]
nyk_night_out = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/2.2 Knicks Night Out - Full Invite List Account IDs.xlsx', sheetname = 'Sheet1')[['acct_id']]
nyk_rookie = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/NYK Rookie Accounts 01117.xlsx', sheetname = 'temp')[['acct_id','email_addr','tag','acct_type']]
nyr_gold = pd.read_excel('/Users/mcnamarp/Downloads/STM Events/Golden Knicks Tenure Event 3_1_17.xlsx', sheetname = 'temp')[['acct_id','email_addr','tag','acct_type']]

# IMPORT ATTENDANCE DATA #
xls = pd.ExcelFile('/Users/mcnamarp/Downloads/STM Events/Event Attendance Numbers with Archtics IDs v lookup.xlsx')
sheets = xls.sheet_names
event_data = pd.DataFrame()
for event in sheets:
	temp = xls.parse(event)
	temp['Event'] = event
	event_data = pd.concat([event_data,temp])

# clean up event data #
event_data['team'] = 'Knicks'
event_data.ix[event_data['Event'].str[:3] == 'NYR', 'team'] = 'Rangers'
event_data['Attended'].replace({0:'No'}, inplace = True)
#event_data.replace({'RSVP':{'Yes':1}}, inplace = True)
event_data = event_data.drop(['Guests Anticipated','Guests Attended','Event'], axis = 1).drop_duplicates().groupby(['team','Ticket Holders']).max().reset_index()

engine = sqlalchemy.create_engine("redshift+psycopg2://USERNAME:PASSWORD@msgbiadb-prod.cqp6htpq4zp6.us-east-1.rds.amazonaws.com:5432/msgbiadb")
renewals_query = '''
SELECT DISTINCT tm_acct_id, lower(email_address) AS email, tm_plan_event_name, regexp_replace(tm_season_name, '^.* ', '') AS team, (NOW()::DATE-tenure_start_date::DATE)/365 AS tenure
FROM ads_main.t_ticket_sales_event_seat
WHERE SUBSTRING(tm_plan_event_name,1,5) IN ('16KFS','17KFS','16RFS','17RFS')
'''
renewals = pd.read_sql(renewals_query, engine)

# REMOVE 2017 FIRST-TIME PLANS #
renewals = renewals[renewals['tenure'] > 0]
renewals.ix[renewals['email'] == 'yvavdiyuk@nydailynews.com', 'email'] = 'nmaheshwari@nydailynews.com'

# REMOVE HVBS #
knicks_hvbs = pd.read_excel('/Users/mcnamarp/Downloads/handler extract - Knicks 2016-17 full season accounts.xlsx', sheetname = 'HVBs')['Acct Id']
knicks_hvbs = list(renewals[(renewals['tm_acct_id'].isin(knicks_hvbs)) & (renewals['team'] == 'Knicks')].index)
rangers_hvbs = pd.read_excel('/Users/mcnamarp/Downloads/handler extract - rangers 2016-17 full season accounts.xlsx', sheetname = 'HVBs')['Acct Id']
rangers_hvbs = list(renewals[(renewals['tm_acct_id'].isin(rangers_hvbs)) & (renewals['team'] == 'Rangers')].index)

renewals = renewals[~renewals.index.isin(rangers_hvbs+knicks_hvbs)]

renewals = renewals.drop_duplicates()
renewal_rates = renewals.groupby(['tm_acct_id','email','team']).count()['tm_plan_event_name'].reset_index().rename(columns = {'tm_plan_event_name':'renewed'})
renewal_rates['renewed'] = renewal_rates['renewed'] - 1

data = pd.merge(renewal_rates, event_data, left_on = ['tm_acct_id','team'], right_on = ['Ticket Holders','team'], how = 'left').drop(['Ticket Holders'], axis = 1)
data[['RSVP','Attended']] = data[['RSVP','Attended']].fillna('No')

data.groupby(['tm_acct_id','team']).mean()['renewed'].groupby(level=1).mean()
data.groupby(['tm_acct_id','team','renewed']).max()['RSVP'].reset_index().groupby(['team','RSVP']).mean()['renewed']
data.groupby(['tm_acct_id','team','renewed']).max()['Attended'].reset_index().groupby(['team','Attended']).mean()['renewed']
data[data['RSVP'] == 'Yes'].groupby(['tm_acct_id','team','renewed']).max()['Attended'].reset_index().groupby(['team','Attended']).mean()['renewed']

data = pd.merge(data, renewals.groupby(['tm_acct_id','team']).max()['tenure'].reset_index(), on = ['tm_acct_id','team'])

# SUMMARY STATS ON MATCHES #
data[['tm_acct_id','team','AGE']].drop_duplicates().groupby('team').mean()['AGE']
data.groupby(['team','RSVP','Attended']).mean()['AGE']

# IMPORTING RETENTION GROUPS #
rangers_retention = pd.read_excel('/Users/mcnamarp/Downloads/Rangers 2016 Retention Scores.final.xlsx', sheetname = 'Scores')
rangers_retention['team'] = 'Rangers'
knicks_retention = pd.read_excel('/Users/mcnamarp/Downloads/Knicks 2016 Retention Scores.final.xlsx', sheetname = 'Scores').rename(columns = {'EMAIL':'Email'})
knicks_retention['team'] = 'Knicks'
retention = rangers_retention.append(knicks_retention, ignore_index = True).rename(columns = {'Segment':'retention_segment'})
retention['Email'] = retention['Email'].str.lower()

# ANALYZING RETENTION GROUPS #
data = pd.merge(data, retention.drop(['Email'], axis = 1), left_on = ['tm_acct_id','team'], right_on = ['acct_id','team']).drop(['acct_id'], axis = 1)
data.groupby(['tm_acct_id','team','renewed','retention_segment']).max()['RSVP'].reset_index().groupby(['team','RSVP','retention_segment']).mean()['renewed']
data[data['RSVP'] == 'Yes'].groupby(['tm_acct_id','team','renewed','retention_segment']).max()['Attended'].reset_index().groupby(['team','Attended','retention_segment']).mean()['renewed']
data[data['retention_segment'] == 'At Risk'].groupby(['tm_acct_id','team','renewed']).max()['RSVP'].reset_index().groupby(['team','RSVP']).mean()['renewed']
data[data['retention_segment'] == 'At Risk'].groupby(['tm_acct_id','team','renewed']).max()['Attended'].reset_index().groupby(['team','Attended']).mean()['renewed']
data[(data['retention_segment'] == 'Rookie') & (data['RSVP'] == 'Yes')].groupby(['tm_acct_id','team','renewed']).max()['Attended'].reset_index().groupby(['team','Attended']).mean()['renewed']

# ADDING EMAIL OPENS DATA #
knicks_opens = pd.read_excel('/Users/mcnamarp/Downloads/Knicks Emails - STM events.xlsx', sheetname = 'Data', parse_cols = [1,5,14])
knicks_opens = knicks_opens[knicks_opens['email_name'] != '160929 MSG NYK Open Practice MISC NEWS']
rangers_opens = pd.read_excel('/Users/mcnamarp/Downloads/Rangers Emails - STM events.xlsx', sheetname = 'Data', parse_cols = [1,5,14])
data = data[data['email'].isin(knicks_opens[knicks_opens['distinctopencnt'] == 1]['email_address'])].append(data[data['email'].isin(rangers_opens[rangers_opens['distinctopencnt'] == 1]['email_address'])])

# COMBINING WITH DEMOGRAPHICS DATA #
demo_indexes = pd.read_csv('/Users/mcnamarp/Downloads/Customer Infobase_170425.txt', usecols = ['EMAIL','INDIVIDUAL_ID'])
demo_indexes['EMAIL'] = demo_indexes['EMAIL'].str.lower()
demo_data = pd.read_csv('/Users/mcnamarp/Downloads/acxiom_customerinfobase_mh.txt').drop(['PERSONIX_LIFESTAGE','PERSONIX_CLUSTER_GROUP','PERSONIX_TIER','DISCRET_INCOME_SCORE','RELIGION','ETHNICITY','INCOME_HIGHRANGES','OCCUPATION'], axis = 1)
demo_data.dropna(subset = ['DISCRET_INCOME_PERCENTILE','AGE','GENDER','EDUCATION','MARITAL_STATUS','PRESENCE_OF_CHILDREN','NETWORTH','INCOME_LOWRANGES'], inplace = True)
demo_data = pd.merge(demo_data, demo_indexes, on = ['INDIVIDUAL_ID']).set_index('INDIVIDUAL_ID').rename(columns = {'EMAIL':'email','INCOME_LOWRANGES':'INCOME','PRESENCE_OF_CHILDREN':'CHILDREN'})
demo_data.replace({'NETWORTH':{'Less than or equal to $0':0,'$1 - $4,999':1,'$5,000 - $9,999':2,'$10,000 - $24,999':4,'$25,000 - $49,999':8,'$50,000 - $99,999':16,'$100,000 - $249,999':32,'$250,000 - $499,999':64,'$500,000 - $999,999':128,'$1,000,000 - $1,999,999':256,'$2,000,000 +':512}}, inplace = True)

data = pd.merge(data, demo_data, on = 'email')

# GETTING DUMMIES #
education_dummies = pd.get_dummies(data['EDUCATION'])
#networth_dummies = pd.get_dummies(data['NETWORTH'])
income_dummies = pd.get_dummies(data['INCOME'])
children_dummies = pd.get_dummies(data['CHILDREN'])
gender_dummies = pd.get_dummies(data['GENDER'])
marital_dummies = pd.get_dummies(data['MARITAL_STATUS'])
team_dummies = pd.get_dummies(data['team'])
rsvp_dummies = pd.get_dummies(data['RSVP'], prefix = 'rsvp')
attended_dummies = pd.get_dummies(data['Attended'], prefix = 'attend')
retention_dummies = pd.get_dummies(data['retention_segment'], prefix = 'retention')
#event_dummies = pd.get_dummies(data['Event']).drop(['NYR 3.21.17 Half Plan HH'], axis = 1)
dummies = children_dummies.join(marital_dummies).join(gender_dummies).rename(columns = {'YES':'CHILDREN'}).join(team_dummies).join(rsvp_dummies).join(attended_dummies).join(retention_dummies)
dummies.drop(['NO','MALE','MARRIED'], axis = 1, inplace = True)


model_data = data.drop(['EDUCATION','INCOME','GENDER','CHILDREN','MARITAL_STATUS','NETWORTH','tm_acct_id','RSVP','Attended','email','team','retention_segment','Score'], axis = 1).join(dummies).drop(['rsvp_No','attend_No'], axis = 1).drop_duplicates()
model_datar = model_data[model_data['Rangers'] == 1].drop(['Knicks','Rangers','retention_Early','retention_Late','DISCRET_INCOME_PERCENTILE','FEMALE','SINGLE','CHILDREN','AGE'], axis = 1)
model_datak = model_data[model_data['Knicks'] == 1].drop(['Knicks','Rangers','retention_25 or More','retention_25 or Less','DISCRET_INCOME_PERCENTILE','FEMALE','SINGLE','CHILDREN','AGE'], axis = 1)
logit = sm.Logit(model_datak['renewed'], model_datak.drop(['renewed'], axis = 1))
result = logit.fit()
result.summary()
np.exp(result.params)

# testing tenure #
tenure = pd.merge(renewals, renewal_rates, on = ['tm_acct_id','email','team'])
knicks_tenure = tenure[tenure['team'] == 'Knicks'].groupby('tenure').mean().reset_index().drop(['tm_acct_id'], axis = 1)
sns.regplot(knicks_tenure['tenure'], knicks_tenure['renewed'], knicks_tenure, color = 'orange')
rangers_tenure = tenure[tenure['team'] == 'Rangers'].groupby('tenure').mean().reset_index().drop(['tm_acct_id'], axis = 1)
sns.regplot(rangers_tenure['tenure'], rangers_tenure['renewed'], rangers_tenure, color = 'blue')
plt.title('The Impact of Tenure on Renewals')
plt.savefig('tenure_17.png')
plt.show()
'''
knicks_tenure_50 = knicks_tenure[knicks_tenure['tenure'] < 50]
sns.regplot(knicks_tenure_50['tenure'], knicks_tenure_50['renewed'], knicks_tenure_50)
rangers_tenure_50 = rangers_tenure[rangers_tenure['tenure'] < 50]
sns.regplot(rangers_tenure_50['tenure'], rangers_tenure_50['renewed'], rangers_tenure_50)

data['tenure_group'] = 'Rookie'
for i in data.index:
	if (data.loc[i,'tenure'] > 20 and data.loc[i,'tenure_group'] == 'Rookie') == True:
		data.loc[i,'tenure_group'] = '20+'
	if (data.loc[i,'tenure'] > 10 and data.loc[i,'tenure_group'] == 'Rookie') == True:
		data.loc[i,'tenure_group'] = '11_20'
	if (data.loc[i,'tenure'] > 5 and data.loc[i,'tenure_group'] == 'Rookie') == True:
		data.loc[i,'tenure_group'] = '6_10'
	if (data.loc[i,'tenure'] > 1 and data.loc[i,'tenure_group'] == 'Rookie') == True:
		data.loc[i,'tenure_group'] = '2_5'
'''

# FIND IDEAL NUMBER OF COMPONENTS #
X = scale(modeling_hockey)
pca = PCA(n_components=35)
pca.fit(X)
var= pca.explained_variance_ratio_
var1=np.cumsum(np.round(pca.explained_variance_ratio_, decimals=4)*100)
plt.plot(var1)

for n_cluster in range(2, 11):
    kmeans = KMeans(n_clusters=n_cluster).fit(modeling_hockey)
    label = kmeans.labels_
    sil_coeff = silhouette_score(modeling_hockey, label, metric='euclidean')
    print("For n_clusters={}, The Silhouette Coefficient is {}".format(n_cluster, sil_coeff))

s = []
for n_clusters in range(2,30):
    kmeans = KMeans(n_clusters=n_clusters)
    kmeans.fit(modeling_bball)
    labels = kmeans.labels_
    centroids = kmeans.cluster_centers_
    s.append(silhouette_score(modeling_bball, labels, metric='euclidean'))

plt.plot(s)
plt.ylabel("Silouette")
plt.xlabel("k")
plt.title("Silouette for K-means cell's behaviour")
sns.despine()