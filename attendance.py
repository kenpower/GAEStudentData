import os
import urllib
import json
import datetime


from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

DEFAULT_GUESTBOOK_NAME = 'default_guestbook'
CLIENT_ID = "343018988663-3u8srl30mnepvteckvdmbjb46hqercha.apps.googleusercontent.com";
CLIENT_SECRET = "37hxyqMHfDzGHgj9tbChMidh";
SCOPE = "https://spreadsheets.google.com/feeds";
REDIRECT_URI = "http://localhost:8080/oauth";
GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/auth';
GOOGLE_TOKEN_URL='https://accounts.google.com/o/oauth2/token';


# We set a parent key on the 'Greetings' to ensure that they are all in the same
# entity group. Queries across the single entity group will be consistent.
# However, the write rate should be limited to ~1/second.

def guestbook_key(guestbook_name=DEFAULT_GUESTBOOK_NAME):
    """Constructs a Datastore key for a Guestbook entity with guestbook_name."""
    return ndb.Key('Guestbook', guestbook_name)

class DatastoreFile(ndb.Model):
  data = ndb.BlobProperty(required=True)
  mimetype = ndb.StringProperty(required=True)

class Greeting(ndb.Model):
    """Models an individual Guestbook entry with author, content, and date."""
    author = ndb.UserProperty()
    content = ndb.StringProperty(indexed=False)
    date = ndb.DateTimeProperty(auto_now_add=True)

class User(ndb.Model):
    '''	models a user of this application
        goggle mail is key'''
    user_id=ndb.StringProperty()
    user = ndb.UserProperty()
    refresh_token=ndb.StringProperty()
    access_token=ndb.StringProperty()
    token_expiry_date=ndb.DateTimeProperty()



class Spreadsheet(ndb.Model):
    spreadsheet_key=ndb.StringProperty()
    user_id=ndb.StringProperty()




class MainPage(webapp2.RequestHandler):

    def get(self):
        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            self.redirect(url)

        '''check if this user laready has ana accout in our application'''
        user_query=User.query(User.user_id == users.get_current_user().user_id())
        user=user_query.get()

        data=""

        if user == None:
            '''request authorisation from google'''
            greetings="not found"

            #details here
            #https://developers.google.com/accounts/docs/OAuth2WebServer

            query_params = {'client_id': CLIENT_ID,
                            'response_type':'code',
                            'scope': SCOPE,
                            'state':'abcd',
                            'login_hint': users.get_current_user().email,
                            'redirect_uri':REDIRECT_URI,
                            'access_type':'offline',
                            'approval_prompt':'force'#forces generation of refresh token
                            }

            url_values = urllib.urlencode(query_params)
            
            
            full_url = GOOGLE_AUTH_URL + '?' + url_values
            self.redirect(full_url) #goto google drive authorisation page

        else:
            greetings="found"
            #go to user front page

        '''
        #debugging stuf only
        template_values = {
            'greetings': data,
            'url': url,
            'fullurl':full_url,
            'url_linktext': url_linktext,
            'userfullname': users.get_current_user().nickname()
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))'''

class CreateUser(webapp2.RequestHandler):
    #called when google redirects from it authorisation page with an oauth code
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(self.request.get('code'))
        self.response.out.write(self.request.get('state'))
        
        query_params = {    'client_id': CLIENT_ID,
                            'code':self.request.get('code'),
                            'client_secret': CLIENT_SECRET,
                            'redirect_uri':REDIRECT_URI,
                            'grant_type':'authorization_code'}

        url_values = urllib.urlencode(query_params)
       
        f = urllib.urlopen(GOOGLE_TOKEN_URL,url_values)
        data=f.read()
        self.response.out.write("\n"+data)
        response_data=json.loads(data)

        
        thisUser=User(user_id=users.get_current_user().user_id(),
            user=users.get_current_user(),
            refresh_token=response_data['refresh_token'],
            access_token=response_data['access_token'],
            token_expiry_date=datetime.datetime.now()+datetime.timedelta(0,response_data['expires_in']))

        thisUser.put()
        
        self.response.out.write("\n")
        self.response.out.write(response_data)





class Newmodule(webapp2.RequestHandler):

	def get(self):
		template_values = {
            'userfullname': users.get_current_user().nickname(),
        }

		template = JINJA_ENVIRONMENT.get_template('newmodule.html')
		self.response.write(template.render(template_values))





class Guestbook(webapp2.RequestHandler):

    def post(self):
        # We set the same parent key on the 'Greeting' to ensure each Greeting
        # is in the same entity group. Queries across the single entity group
        # will be consistent. However, the write rate to a single entity group
        # should be limited to ~1/second.
        guestbook_name = self.request.get('guestbook_name',
                                          DEFAULT_GUESTBOOK_NAME)
        greeting = Greeting(parent=guestbook_key(guestbook_name))

        if users.get_current_user():
            greeting.author = users.get_current_user()

        greeting.content = self.request.get('content')
        greeting.put()

        query_params = {'guestbook_name': guestbook_name}
        self.redirect('/?' + urllib.urlencode(query_params))


application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/oauth',CreateUser),
    ('/newmodule', Newmodule),
], debug=True)