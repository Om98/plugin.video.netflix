from __future__ import unicode_literals

import json
import re
import sys
import urllib
import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

import add
import connect
import delete
import get
import login
import profiles
import utility

plugin_handle = int(sys.argv[1])


def videos(url, video_type, run_as_widget=False):
    loading_progress = None
    if not run_as_widget:
        loading_progress = xbmcgui.DialogProgress()
        loading_progress.create('Netflix', utility.get_string(30205) + '...')
        utility.progress_window(loading_progress, 0, '...')
    xbmcplugin.setContent(plugin_handle, 'movies')
    if not xbmcvfs.exists(utility.session_file()):
        login.login()
    content = utility.decode(connect.load_site(url))
    if not 'id="page-LOGIN"' in content:
        if utility.get_setting('single_profile') == 'true' and 'id="page-ProfilesGate"' in content:
            profiles.force_choose()
        else:
            if '<div id="queue"' in content:
                content = content[content.find('<div id="queue"'):]
            content = utility.clean_content(content)
            match = None
            if not match: match = re.compile('"\$type":"leaf",.*?"id":([0-9]+)', re.DOTALL).findall(content)
            print '1: ' + str(match)
            if not match: match = re.compile('<a href="\/watch\/([0-9]+)', re.DOTALL).findall(content)
            print '2: ' + str(match)
            if not match: match = re.compile('<span id="dbs(.+?)_.+?alt=".+?"', re.DOTALL).findall(content)
            print '3: ' + str(match)
            if not match: match = re.compile('<span class="title.*?"><a id="b(.+?)_', re.DOTALL).findall(content)
            print '4: ' + str(match)
            if not match: match = re.compile('"boxart":".+?","titleId":(.+?),', re.DOTALL).findall(content)
            print '5: ' + str(match)
            if not match: match = re.compile('WiPlayer\?movieid=([0-9]+?)&', re.DOTALL).findall(content)
            print '6: ' + str(match)
            print len(match)
            i = 1
            for video_id in match:
                if int(video_id) > 10000000:
                    if not run_as_widget:
                        utility.progress_window(loading_progress, i * 100 / len(match), '...')
                    video(video_id, '', '', False, False, video_type, url)
                i += 1
            match1 = re.compile('&pn=(.+?)&', re.DOTALL).findall(url)
            match2 = re.compile('&from=(.+?)&', re.DOTALL).findall(url)
            match_api_root = re.compile('"API_ROOT":"(.+?)"', re.DOTALL).findall(content)
            match_api_base = re.compile('"API_BASE_URL":"(.+?)"', re.DOTALL).findall(content)
            match_identifier = re.compile('"BUILD_IDENTIFIER":"(.+?)"', re.DOTALL).findall(content)
            if 'agid=' in url and match_api_root and match_api_base and match_identifier:
                genre_id = url[url.find('agid=') + 5:]
                add.directory(utility.get_string(30110), match_api_root[0] + match_api_base[0] + '/' + match_identifier[
                    0] + '/wigenre?genreId=' + genre_id + '&full=false&from=51&to=100&_retry=0', 'list_videos', '',
                              video_type)
            elif match1:
                current_page = match1[0]
                next_page = str(int(current_page) + 1)
                add.directory(utility.get_string(30110),
                              url.replace('&pn=' + current_page + '&', '&pn=' + next_page + '&'), 'list_videos', '',
                              video_type)
            elif match2:
                current_from = match2[0]
                next_from = str(int(current_from) + 50)
                current_to = str(int(current_from) + 49)
                next_to = str(int(current_from) + 99)
                add.directory(utility.get_string(30110),
                              url.replace('&from=' + current_from + '&', '&from=' + next_from + '&').replace(
                                  '&to=' + current_to + '&', '&to=' + next_to + '&'), 'list_videos', '', video_type)
            if utility.get_setting('force_view') == 'true' and not run_as_widget:
                xbmc.executebuiltin('Container.SetViewMode(' + utility.get_setting('view_id_videos') + ')')
        xbmcplugin.endOfDirectory(plugin_handle)
    else:
        delete.cookies()
        utility.log('User is not logged in.', loglevel=xbmc.LOGERROR)
        utility.notification(utility.get_string(30303))


def video(video_id, title, thumb_url, is_episode, hide_movies, video_type, url):
    added = False
    year = ''
    mpaa = ''
    duration = ''
    description = ''
    director = ''
    genre = ''
    rating = 0.0
    video_details = get.video_info(video_id)
    match = re.compile('<span class="title.*?>(.+?)</span', re.DOTALL).findall(video_details)
    if not title:
        title = match[0].strip()
    match = re.compile('<span class="year.*?>(.+?)</span', re.DOTALL).findall(video_details)
    if match:
        year = match[0].partition('-')[0]
    if not thumb_url:
        match = re.compile('src="(.+?)"', re.DOTALL).findall(video_details)
        thumb_url = match[0].replace('/webp/', '/images/').replace('.webp', '.jpg')
    match = re.compile('<span class="mpaaRating.*?>(.+?)</span', re.DOTALL).findall(video_details)
    if match:
        mpaa = match[0].strip()
    match = re.compile('<span class="duration.*?>(.+?)</span', re.DOTALL).findall(video_details)
    if match:
        duration = match[0].lower()
    if duration.split(' ')[-1].startswith('min'):
        type = 'movie'
        video_type_temp = type
        duration = duration.split(' ')[0]
    else:
        video_type_temp = 'tv'
        if is_episode:
            type = 'episode'
        else:
            type = 'tvshow'
        duration = ''
    if utility.get_setting('use_tmdb') == 'true':
        year_temp = year
        title_temp = title
        if ' - ' in title_temp:
            title_temp = title_temp[title_temp.index(' - '):]
        if '-' in year_temp:
            year_temp = year_temp.split('-')[0]
        filename = utility.clean_filename(video_id) + '.jpg'
        filename_none = utility.clean_filename(video_id) + '.none'
        cover_file = xbmc.translatePath(utility.cover_cache_dir() + filename)
        cover_file_none = xbmc.translatePath(utility.cover_cache_dir() + filename_none)
        if not (xbmcvfs.exists(cover_file) or xbmcvfs.exists(cover_file_none)):
            utility.log('Downloading cover art. type: %s, video_id: %s, title: %s, year: %s' % (video_type_temp,
                                                                                                video_id, title_temp,
                                                                                                year_temp))
            get.cover(video_type_temp, video_id, title_temp, year_temp)
    match = re.compile('src=".+?">.*?<.*?>(.+?)<', re.DOTALL).findall(video_details)
    if match:
        description_temp = match[0]
        # replace all embedded unicode in unicode (Norwegian problem)
        description_temp = description_temp.replace('u2013', unicode('\u2013')).replace('u2026', unicode('\u2026'))
        description = utility.unescape(description_temp)
    match = re.compile('Director:</dt><dd>(.+?)<', re.DOTALL).findall(video_details)
    if match:
        director = match[0].strip()
    match = re.compile('<span class="genre.*?>(.+?)</span', re.DOTALL).findall(video_details)
    if match:
        genre = match[0]
    match = re.compile('<span class="rating">(.+?)</span', re.DOTALL).findall(video_details)
    if len(match) > 0:
        rating = float(match[0])
    title = utility.unescape(title)
    next_mode = 'play_video_main'
    if utility.get_setting('browse_tv_shows') == 'true' and type == 'tvshow':
        next_mode = 'list_seasons'
    if '/my-list' in url and video_type_temp == video_type:
        add.video(title, video_id, next_mode, thumb_url, type, description, duration, year, mpaa,
                  director, genre, rating, remove=True)
        added = True
    elif type == 'movie' and hide_movies:
        pass
    elif video_type_temp == video_type or video_type == 'both':
        add.video(title, video_id, next_mode, thumb_url, type, description, duration, year, mpaa,
                  director, genre, rating)
        added = True
    return added


def genres(video_type):
    post_data = ''
    match = []
    xbmcplugin.addSortMethod(plugin_handle, xbmcplugin.SORT_METHOD_LABEL)
    if not xbmcvfs.exists(utility.session_file()):
        login.login()
    if video_type == 'tv':
        post_data = '{"paths":[["genres",83,"subgenres",{"from":0,"to":20},"summary"],["genres",83,"subgenres",' \
                    '"summary"]],"authURL":"%s"}' % utility.get_setting('authorization_url')
    elif video_type == 'movie':
        post_data = '{"paths":[["genreList",{"from":0,"to":24},["id","menuName"]],["genreList"]],"authURL":"%s"}' \
                    % utility.get_setting('authorization_url')
    else:
        pass
    content = utility.decode(connect.load_site(
        utility.evaluator_url % (utility.get_setting('netflix_application'), utility.get_setting('netflix_version')),
        post=post_data))
    matches = json.loads(content)['value']['genres']
    for k in matches:
        try:
            match.append((unicode(matches[k]['id']), matches[k]['menuName']))
        except Exception:
            try:
                match.append((unicode(matches[k]['summary']['id']), matches[k]['summary']['menuName']))
            except Exception:
                pass
    for genre_id, title in match:
        if video_type == 'tv':
            add.directory(title, utility.main_url + '/browse/genre/' + genre_id + '?bc=83', 'list_videos', '',
                          video_type)
        elif not genre_id == '83' and video_type == 'movie':
            add.directory(title, utility.main_url + '/browse/genre/' + genre_id, 'list_videos', '', video_type)
    xbmcplugin.endOfDirectory(plugin_handle)


def view_activity(video_type, run_as_widget=False):
    count = 0
    video_ids = []
    loading_progress = None
    if not run_as_widget:
        loading_progress = xbmcgui.DialogProgress()
        loading_progress.create('Netflix', utility.get_string(30205) + '...')
        utility.progress_window(loading_progress, 0, '...')
    xbmcplugin.setContent(plugin_handle, 'movies')
    if not xbmcvfs.exists(utility.session_file()):
        login.login()
    content = utility.decode(connect.load_site(utility.main_url + '/WiViewingActivity'))
    series_id = re.compile('(<li .*?data-series=.*?</li>)', re.DOTALL).findall(content)
    for i in range(1, len(series_id), 1):
        entry = series_id[i]
        if not run_as_widget:
            utility.progress_window(loading_progress, (count + 1) * 100 / len(series_id), '...')
        match_id = re.compile('data-movieid="(.*?)"', re.DOTALL).findall(entry)
        if match_id:
            video_id = match_id[0]
        match = re.compile('class="col date nowrap">(.+?)<', re.DOTALL).findall(entry)
        date = match[0]
        match_title1 = re.compile('class="seriestitle">(.+?)</a>', re.DOTALL).findall(entry)
        match_title2 = re.compile('class="col title">.+?>(.+?)<', re.DOTALL).findall(entry)
        if match_title1:
            title = utility.unescape(match_title1[0]).replace('</span>', '')
        elif match_title2:
            title = match_title2[0]
        else:
            title = ''
        title = date + ' - ' + title
        if video_id not in video_ids:
            video_ids.append(video_id)
            # due to limitations in the netflix api, there is no way to get the series_id of an
            # episode, so the 4 param is set to True to treat tv episodes the same as movies.
            added = video(video_id, title, '', True, False, video_type, '')
            if added:
                count += 1
            if count == 20:
                break
    if utility.get_setting('force_view') and not run_as_widget:
        xbmc.executebuiltin('Container.SetViewMode(' + utility.get_setting('view_id_activity') + ')')
    xbmcplugin.endOfDirectory(plugin_handle)


def search(search_string, video_type, run_as_widget=False):
    i = 1
    loading_progress = None
    if not run_as_widget:
        loading_progress = xbmcgui.DialogProgress()
        loading_progress.create('Netflix', utility.get_string(30205) + '...')
        utility.progress_window(loading_progress, 0, '...')
    xbmcplugin.setContent(plugin_handle, 'movies')
    if not xbmcvfs.exists(utility.session_file()):
        login.login()
    post_data = '{"paths":[["search","%s",{"from":0,"to":48},["summary","title"]],["search","%s",["id","length",' \
                '"name","trackIds","requestId"]]],"authURL":"%s"}' % (search_string, search_string,
                                                                      utility.get_setting('authorization_url'))
    content = utility.decode(connect.load_site(
        utility.evaluator_url % (utility.get_setting('netflix_application'), utility.get_setting('netflix_version')),
        post=post_data))
    try:
        matches = json.loads(content)['value']['videos']
        for k in matches:
            if not run_as_widget:
                utility.progress_window(loading_progress, i * 100 / len(matches), '...')
            video(unicode(matches[k]['summary']['id']), '', '', False, False, video_type, '')
            i += 1
        if utility.get_setting('force_view') and not run_as_widget:
            xbmc.executebuiltin('Container.SetViewMode(' + utility.get_setting('view_id_videos') + ')')
        xbmcplugin.endOfDirectory(plugin_handle)
    except Exception:
        utility.notification(utility.get_string(30306))
        pass


def seasons(series_name, series_id, thumb):
    seasons = []
    content = get.series_info(series_id)
    content = json.loads(content)['video']['seasons']
    for item in content:
        seasons.append((item['title'], item['seq']))
    for season in seasons:
        add.season(season[0], season[1], 'list_episodes', thumb, series_name, series_id)
    xbmcplugin.endOfDirectory(plugin_handle)


def episodes(series_id, season):
    xbmcplugin.setContent(plugin_handle, 'episodes')
    content = get.series_info(series_id)
    content = json.loads(content)['video']['seasons']
    for test in content:
        episode_season = unicode(test['seq'])
        if episode_season == season:
            for item in test['episodes']:
                episode_id = item['episodeId']
                episode_nr = item['seq']
                episode_title = (unicode(episode_nr) + '. ' + item['title'])
                duration = item['runtime']
                offset = item['bookmark']['offset']
                playcount = 0
                if (duration > 0 and float(offset) / float(duration)) >= 0.9:
                    playcount = 1
                description = item['synopsis']
                try:
                    thumb = item['stills'][0]['url']
                except:
                    thumb = utility.addon_fanart()
                add.episode(episode_title, episode_id, 'play_video_main', thumb, description, duration, season,
                            episode_nr, series_id, playcount)
    if utility.get_setting('force_view'):
        xbmc.executebuiltin('Container.SetViewMode(' + utility.get_setting('view_id_episodes') + ')')
    xbmcplugin.endOfDirectory(plugin_handle)


"""
alle serien anzeigen
{"paths":[["genres",83,"su",{"from":0,"to":400},["summary","title"]]],"authURL":"%s"}

jeweiliges movie genre anzeigen
{"paths":[["genres",<genre_id>,"su",{"from":0,"to":120},["summary","title"]]],"%s"}
"""
