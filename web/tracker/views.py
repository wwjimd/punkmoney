from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from tracker.models import *
from django.template import Context, loader, RequestContext
from datetime import datetime
from operator import itemgetter
from itertools import chain
from django.db.models import Q
from django.utils import simplejson
import re
import operator

# Create your views here.

def home(request):
    return render_to_response('home.html')

def tracker(request, tag_1 = None, tag_2 = None, tag_3 = None):

    # convert tags to ids and get related tags
    
    tag_ids = []
    tag_slug = ''
    for tag in [tag_1, tag_2, tag_3]:
        if tag is not None:
            t = tags.objects.get(tag = tag)
            tag_id = int(t.id)
            tag_ids.append(tag_id)  
        
            tag_slug += tag + '/'

    variables = {
        'page':'ticker',
        'tag_1':tag_1,
        'tag_2':tag_2,
        'tag_3':tag_3,
        'tag_slug' : tag_slug,
    }

    # Related tags
    related_tags = relatedTags(tag_ids)
    
    if related_tags is not None:
        variables['related_tags'] = related_tags

    return render_to_response('tracker.html', variables)


def ticker(
        request, 
        max=50, 
        type=None, 
        username=None, 
        noteid=None, 
        tag_1=None, 
        tag_2=None, 
        tag_3=None,
    ):

    # limit max to 200
    max = int(max)
    if max > 200:
        max = 200
        
    # temporary workaround
    if type == '99':
        type = '0'
     
    # Convert tags to ids
    filters = []
    
    if tag_1 is not None:
        tag_1 = tags.objects.get(tag = tag_1)
        filters.append(int(tag_1.id))

    if tag_2 is not None:
        tag_2 = tags.objects.get(tag = tag_2)
        filters.append(int(tag_2.id))
        
    if tag_3 is not None:
        tag_3 = tags.objects.get(tag = tag_3)
        filters.append(int(tag_3.id))
    
    new_events = []
    
    # Filter by tags
    if len(filters) > 0:
    
        if type is not None:
            raw_events = events.objects.filter(
                Q(type=type)
            ).order_by('-timestamp')[:max]
        else:
            raw_events = events.objects.all().order_by('-timestamp')[:max]
    
        
        for event in raw_events:
            note_id = event.note_id
            
            try:
                tweet = tweets.objects.get(tweet_id = note_id)
                tweet_tags = [tweet.tag_1, tweet.tag_2, tweet.tag_3]
                tweet_tags = [int(tag) for tag in tweet_tags if tag is not None]

                if len(filters) == 1:
                    if filters[0] in tweet_tags:
                        new_events.append(event)

                if len(filters) == 2:
                
                    if filters[0] in tweet_tags and filters[1] in tweet_tags:
                        new_events.append(event)
                        
                if len(filters) == 3:
                    if filters[0] in tweet_tags and filters[1] in tweet_tags and filters[2] in tweet_tags:
                        new_events.append(event)
            except:
                pass

    # filter by type and/or username if given
    #  | Q(to_user=username)
    elif type is not None and username is not None:
    
        if type == '0':
        
            print 'test'
    
            new_events = events.objects.filter(
                Q(type=type),
                Q(from_user=username)
                ).order_by('-timestamp')[:max]
                
        elif type == '1':
        
            new_events = events.objects.filter(
                Q(type=type),
                Q(to_user=username)
                ).order_by('-timestamp')[:max]
            
    elif type is not None and username is None:
        new_events = events.objects.filter(
            Q(type=type)
            ).order_by('-timestamp')[:max]
    elif type is None and username is not None:
        new_events = events.objects.filter(
            Q(from_user=username) | Q(to_user=username)
            ).order_by('-timestamp')[:max]
    elif noteid is not None:
        new_events = events.objects.filter(
            Q(note_id=noteid)
            ).order_by('-timestamp')[:max]
    else:
        new_events = events.objects.all().order_by('-timestamp')[:max]

        
    # get new notes
    new_notes = notes.objects.all()    
    result_list = []
    
    for event in new_events:
        note = notes.objects.filter(id=event.note_id)[0]
        
        if int(note.status) != 0 and type is not None:
            if int(type) == 4 or int(type) == 5:
                continue
        
        # Turn tags into hyperlinks in promise
        note_id = event.note_id
        tweet = tweets.objects.get(tweet_id = note_id)
        tag_ids = [tweet.tag_1, tweet.tag_2, tweet.tag_3]
        tag_ids = [int(tag) for tag in tag_ids if tag is not None]
        
        tags_final = []
        for tag_id in tag_ids:
            try:
                t = tags.objects.get(id = tag_id)
                if t is not None:
                    tag = str(t.tag)
                    tags_final.append(tag)
            except:
                pass
            
        if event.note_id == note.id:
            
            result_list.append({
                'promise':note.promise,
                'timestamp':event.timestamp,
                'from_user':event.from_user,
                'to_user':event.to_user,
                'type':event.type,
                'note_id':event.note_id,
                'tweet_id':event.tweet_id,
                'tags':tags_final,
            })
    
    final = sorted(result_list, key=itemgetter('timestamp'), reverse=True)
    
    # arrow on or off
    if noteid is not None:
        show_arrow = False
    else:
        show_arrow = True
    
    variables = {
        'events':final,
        'show_arrow':show_arrow
    }

    return render_to_response('ticker.html', variables)    


def user(request, username):

    variables = {}

    notes_bearer = notes.objects.filter(bearer=username).filter(status=0)
    notes_issuer = notes.objects.filter(issuer=username).filter(status=0)
    events_from = events.objects.filter(from_user=username)[:10]
    events_to = events.objects.filter(to_user=username)[:10]
 
    events_all = chain(events_from,events_to)
    
    result_list = []
    
    for event in events_all:
        note = notes.objects.filter(id=event.note_id)[0]
        if event.note_id == note.id:
        
            result_list.append({
                'promise':note.promise,
                'timestamp':event.timestamp,
                'from_user':event.from_user,
                'to_user':event.to_user,
                'type':event.type,
                'note_id':event.note_id,
                'tweet_id':event.tweet_id,
            })
    
    final = sorted(result_list, key=itemgetter('timestamp'), reverse=True)
    
    # Find number of people who trust this user
    trusters = trustlist.objects.filter(trusted=username)    
    trust_num = len(trusters)

    # Add trusters to list
    trusters_list = []
    for truster in trusters:
        trusters_list.append(truster.user)

    # Arbitrary, for now
    top_trusters = trusters_list[:1]

    # generate slug
    slug = username
    
    # karma
    karma = getKarma(username)
    
    # combine events
    variables = {
        'username':username,
        'notes_held':notes_bearer,
        'notes_issued':notes_issuer,
        'events':final,
        'trust':trust_num,
        'trusters':trusters_list,
        'top_trusters':top_trusters,
        'karma':karma,
    }
    
    # return all
    return render_to_response('user.html', variables)
    

def getnote(request, noteid):

    note = notes.objects.get(id=noteid)
    new_events = events.objects.filter(note_id=noteid).order_by('timestamp')
    new_events = new_events.reverse()
    
    tweet = tweets.objects.get(tweet_id=noteid)
    
    id = str(note.id)
    
    promise = note.promise
    
    # Replace pronouns with opposites
    variables = {}
    
    if note.type == 5 or note.type == 10:
        reply_promise = promise.replace(' my ', ' your ')
        reply_promise = reply_promise.replace(' me ', ' you ')
        reply_promise = reply_promise.replace(' i ', ' you ')
        variables['reply_promise'] = reply_promise
    
    raw_tags = [tweet.tag_1, tweet.tag_2, tweet.tag_3]
    tags_final = []
    for tag_id in raw_tags:
        if tag_id != None:
            t = tags.objects.get(id = tag_id)
            tags_final.append(t.tag)
            
    # trust
    issuer_trust = getKarma(note.issuer)
    bearer_trust = getKarma(note.bearer)
    
    variables = {
        'events' : new_events,
        'note' : note,
        'content' : tweet.content,
        'url' : tweet.url,
        'issuer_trust' : issuer_trust,
        'bearer_trust' : bearer_trust,
        'display_url' : tweet.display_url,
        'id' : id,
        'img_url' : tweet.img_url,
        'tags' : tags_final,
    }
    
    if note.type == 0:
        template = 'note.html'
    elif note.type == 4:
        template = 'offer.html'
    elif note.type == 5:
        template = 'need.html'
    elif note.type == 1:
        template = 'thanks.html'
    elif note.type == 10:
        template = 'request.html'
    
    return render_to_response(template, variables)
    
    
def printer(request):
    variables = {
        'page':'printer',
    }
    return render_to_response('printer.html', variables)
    

def help(request):
    variables = {
        'page':'help',
    }
    return render_to_response('help.html', variables)

# [!] Check if for non-note ids too
def search(request, term=None):

    # Attempt to resolve to username first
    try:
        user = users.objects.get(username=term)
        url = '/user/' + term
    except:
        # Otherwise, resolve to tags
        tags = term.split(' ')
        
        url = '/t/'
        
        for tag in tags:
            url += tag + '/'
        
    return HttpResponse(url)


'''
API Methods
'''
''' HELPERS '''

# getKarma
# fethes and returns a user's karma, based on promises redeemed from user by others

def getKarma(username):

    # Disabled for now
    try:
        redemptions = notes.objects.filter(status=1).filter(issuer=username)
        trust = len(redemptions)
        
        return trust
    except:
        return 0


# relatedTags
# gets frequently associated tags to the supplied tags list

def relatedTags(base_tags = None):

    all_tweets = []
    # If no tag is specified, return most popular tags
    if base_tags is None or base_tags == []:
        all_tweets = tweets.objects.filter(parsed = 1)
    else:
        raw_tweets = []
        for tag_id in base_tags:
            raw_tweets += tweets.objects.filter(
                Q(tag_1 = tag_id)|Q(tag_2 = tag_id)|Q(tag_3 = tag_id)
            )

        # Filter out tweets where tags don't co-occur
        for tweet in raw_tweets:
        
            tweet_tags = [tweet.tag_1, tweet.tag_2, tweet.tag_3]
            tweet_tags = [int(tag) for tag in tweet_tags if tag is not None]
            
            insert = True
            for tag in base_tags:
                if tag not in tweet_tags:
                    insert = False
                    break

            if insert == True:
                all_tweets.append(tweet)

    # Get and rank all tags
    all_tags = {}
    for tweet in all_tweets:
    
        tweet_tags = [tweet.tag_1, tweet.tag_2, tweet.tag_3]
        tweet_tags = [int(tag) for tag in tweet_tags if tag is not None]
        
        for tag in tweet_tags:
        
            if all_tags.has_key(tag) is False:
                all_tags[tag] = 1
            else:
                all_tags[tag] = all_tags[tag] + 1

    
    # Get names for all tags
    tags_final = {}
    
    for tag_id, count in all_tags.items():
        try:
            if base_tags is not None:
                if tag_id not in base_tags:         
                    t = tags.objects.get(id = tag_id)
                    tag = str(t.tag)
                    tags_final[tag] = count
            else:
                t = tags.objects.get(id = tag_id)
                tag = str(t.tag)
                tags_final[tag] = count
        except Exception, e:
            print e
            
    # Sort dict by count, limit to first 20
    
    tags_final = sorted(tags_final.iteritems(), key=operator.itemgetter(1))
    tags_final.reverse()

    
    # Return tags    
    return tags_final
    

