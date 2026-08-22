import pytest
import scraper.settings as settings
import scraper.scraper as scp
from unittest.mock import MagicMock, patch, Mock, call
import pathlib
import sqlite3
import os
import requests, queue
import json
import shared.db_scheme as dbs

# TODO : Add fixture for full information cases when scraping MAL profiles 

def make_http_error(status_code):
    response = requests.Response()
    response.status_code = status_code
    return requests.exceptions.HTTPError(response=response)

@pytest.fixture
def test_settings(tmp_path) -> settings.ParametersScraper:
    params = settings.ParametersScraper(
        PROFILER_PATH = tmp_path / "scraper_test.prof",
        DB_PATH = tmp_path / "scraper_test.db",
        LOG_PATH = tmp_path / "scraper_test.log",
        DUMP_PATH = os.environ.get("DUMP_PATH", "./data/dump.sql"),
        MIN_SLEEP = 6,
        MAX_USERS = 3,
        CONNECTION_ISSUES_SLEEP = 0,
        QUEUE_TIMEOUT = 0.5,
        RATE_LIMIT_SLEEP = 0
    )
    return params

@pytest.fixture
def mock_params_empty():
    mock_settings = MagicMock()
    mock_settings.model_dump.return_value = {
            "MIN_ENTRIES": 5,
            "MIN_SLEEP" : 1
        }
    return mock_settings

@pytest.fixture
def mock_conn():
    conn_mock = MagicMock()
    return conn_mock

@pytest.fixture
def db_session(test_settings) :
    test_settings = test_settings.model_dump() # Tiny fix, choose between modifying the class specifications or keep .model_dump()
    conn = sqlite3.connect(test_settings["DB_PATH"])
    yield conn
    conn.close()

class TestScraperConstructor:
    @pytest.fixture
    def mock_session(self):
        return MagicMock()

    @pytest.fixture
    def scraper_empty(self, mock_params_empty, mock_session, mock_conn):
        return scp.Scraper(params=mock_params_empty, session=mock_session, conn=mock_conn)

    def test_scraper_constructor_init_param(self, test_settings, mock_session, mock_conn):
        scraper = scp.Scraper(params=test_settings, session=mock_session, conn=mock_conn)
        assert mock_session is scraper.session
        assert test_settings.model_dump() == scraper.params
        assert scraper.user_page_sleep == 6

    def test_scraper_constructor(self, scraper_empty):
        assert scraper_empty.seen == set()
        assert scraper_empty.added == set()
    
    def test_fetch_user_page(self,  scraper_empty):
        path_html = "scraper/tests/fixtures/mal_user_page.html"
        with open(path_html) as f:
            html = f.read()
        with patch.object(scraper_empty, 'fetch_html', return_value = html) as mock_fetch:
            result = scraper_empty.fetch_user_page(sleep_time=0)

        #From fixture mal_user_page.html (Last update 13/07/26)
        expected_result = ["MadAniLoverDhya","FQ-400","VizslaStyle","peritheplatypus","Davisd","Sindox","tchu3","SrP_1105","naverkung","tenoriio","Fox_Cato","quazum1","Zengkoy","KKete","clannis","pavel_kun","SalPed","AnonymouS6","Naire_","zFrankFF"]
        mock_fetch.assert_called_once_with("https://myanimelist.net/users.php")
        assert type(result) == list
        assert result == expected_result
    
    def test_find_friends(self, scraper_empty):
        path_html = "scraper/tests/fixtures/mal_friend_page.net.html"
        with open(path_html) as f:
            text_html = f.read()
        
        with patch.object(scraper_empty, "fetch_html", return_value=text_html) as mock_fetch_friend:
            res = scraper_empty.find_friends(name="Matmath", sleep_time=0)
        
        mock_fetch_friend.assert_called_once_with("https://myanimelist.net/profile/Matmath/friends")
        assert type(res) == list
        assert res == ["FallenTiki", "ZeIdriss", "darkelsyum", "Hyez"]
    
    def test_fetch_manga_profile(self, scraper_empty):
        path_html = "scraper/tests/fixtures/mal_profile_page.html"
        with open(path_html) as f:
            text_html = f.read()
        
        with patch.object(scraper_empty, "fetch_html", return_value=text_html) as mock_fetch_html:
            with patch.object(scraper_empty, "find_friends", return_value=["User1"]) as mock_fetch_friends:
                res = scraper_empty.fetch_manga_profile("Matmath", sleep_time=0)
        
        mock_fetch_html.assert_called_once_with("https://myanimelist.net/profile/Matmath")
        assert type(res) == dict
        assert res == {"username" : "Matmath", "gender" : None, "birthday" : None, "location" : None, "entries" : 126, "friends" : ["User1"]}

    def test_collect_manga_data(self, scraper_empty):
        json_path = "scraper/tests/fixtures/load.json"
        with open(json_path) as json_data:
            data = json.load(json_data)
        
        n_entry = len(data)
        with patch.object(scraper_empty, "fetch_json", return_value=data) as mock_fetch_json:
            res = scraper_empty.collect_manga_data("Matmath", n_entry, sleep_time=0)

        mock_fetch_json.assert_called_once_with("https://myanimelist.net/mangalist/Matmath/load.json", params={"offset" : 0})
        assert len(res) == 1
        assert len(res[0]) == n_entry


class TestScraperDynamicComputation:

    @pytest.mark.parametrize(
        "min_sleep,max_sleep,max_users,q_size,n_added,exp_factor,expected",
        [(1.0,10.0,100,50, 100,9,10.0),
         (1.0,10.0,100,0,0,9,1.0),
         (1.0,10.0,100,500,20,9,10.0),
         pytest.param(1.0,10.0,100,40,30,9,1.0, marks=pytest.mark.xfail),
         pytest.param(1.0,100.0,100,20,15,2,1.0, marks=pytest.mark.xfail)
        ]
    )
    def test_compute_dynamic_sleep(self, min_sleep, max_sleep, max_users, q_size, n_added, exp_factor, expected, mock_conn):
        mock_settings = MagicMock()
        mock_settings.model_dump.return_value = {
                "MIN_SLEEP" : min_sleep,
                "MAX_USERS" : max_users,
                "MAX_SLEEP" : max_sleep,
            }
        
        scraper = scp.Scraper(mock_settings, session=MagicMock(), conn=mock_conn)
        res = scraper.compute_dynamic_sleep(q_size,n_added,exp_factor)
        assert res == expected

class TestScraperFetchRequestsMethods:
    @pytest.fixture
    def scraper_instance(self, mock_params_empty, mock_conn) -> scp.Scraper:
        mock_http_session = MagicMock()
        mock_http_session.get.return_value = MagicMock(
            **{
                "raise_for_status" : lambda: None,
                "text": "SCRAPER TEST",
                "json" : lambda : {"data" : []}
            }
        )
        return scp.Scraper(session= mock_http_session, params=mock_params_empty, conn=mock_conn)

    def test_scraper_html_fetch(self, scraper_instance : scp.Scraper):
        text = scraper_instance.fetch_html("fake_url")
        assert text == "SCRAPER TEST"

    def test_scraper_json_fetch(self, scraper_instance : scp.Scraper):
        json = scraper_instance.fetch_json("fake_url")
        assert json["data"] == []

class TestErrorFetchRequests:  
    @pytest.fixture
    def scraper_instance(self, request, mock_params_empty, mock_conn) -> scp.Scraper:
        mock_http_session = MagicMock()
        res = MagicMock()

        res.status_code = request.param
        res.raise_for_status.side_effect = requests.exceptions.HTTPError()

        mock_http_session.get.return_value = res

        return scp.Scraper(session= mock_http_session, params=mock_params_empty, conn=mock_conn)

    @pytest.mark.parametrize("scraper_instance", [404,429,403,401,408,405], indirect=True)
    def test_error_scraper_html_fetch(self, scraper_instance):
        with pytest.raises(requests.exceptions.RequestException):
            text = scraper_instance.fetch_html("fake_url")

    @pytest.mark.parametrize("scraper_instance", [404,429,403,401,408,405], indirect=True)
    def test_error_scraper_json_fetch(self, scraper_instance):
        with pytest.raises(requests.exceptions.RequestException):
            json = scraper_instance.fetch_json("fake_url")

class TestScraperDBInterraction:

    @pytest.fixture
    def scp_db(self, test_settings, db_session):
        scraper = scp.Scraper(params=test_settings, conn=db_session, session=MagicMock())
        return scraper
    
    @pytest.mark.parametrize("data,expected_added",
        [ ([{'manga_id' : 6, 'status' : 5, 'num_read_chapters' : 30, 'score' : 9, 'start_date_string' : '', 'finish_date_string' : ''},
            {'manga_id' : 6, 'status' : 5, 'num_read_chapters' : 30, 'score' : 9, 'start_date_string' : '', 'finish_date_string' : ''},
            {'manga_id' : 6, 'status' : 5, 'num_read_chapters' : 30, 'score' : 9, 'start_date_string' : '', 'finish_date_string' : ''}],0),

          ([{'manga_id' : 6, 'status' : 2, 'num_read_chapters' : 30, 'score' : 9, 'start_date_string' : '', 'finish_date_string' : ''},
            {'manga_id' : 6, 'status' : 2, 'num_read_chapters' : 30, 'score' : 9, 'start_date_string' : '', 'finish_date_string' : ''},
            {'manga_id' : 6, 'status' : 2, 'num_read_chapters' : 30, 'score' : 9, 'start_date_string' : '', 'finish_date_string' : ''}],1),

          ([{'manga_id' : 6, 'status' : 6, 'num_read_chapters' : 30, 'score' : 9, 'start_date_string' : '', 'finish_date_string' : ''},
            {'manga_id' : 8, 'status' : 2, 'num_read_chapters' : 50, 'score' : 10, 'start_date_string' : '11-25-23', 'finish_date_string' : '11-29-25'},
            {'manga_id' : 192, 'status' : 1, 'num_read_chapters' : 14, 'score' : 7, 'start_date_string' : '', 'finish_date_string' : ''}], 3),

        
          ([{'manga_id' : 6, 'status' : 6, 'num_read_chapters' : 30, 'score' : 9, 'start_date_string' : '', 'finish_date_string' : ''},
            {'manga_id' : 8, 'status' : 2, 'num_read_chapters' : 50, 'score' : 10, 'start_date_string' : '11-25-23', 'finish_date_string' : '11-29-25'},
            {'manga_id' : 192, 'status' : 1, 'num_read_chapters' : 14, 'score' : 7, 'start_date_string' : '', 'finish_date_string' : ''}], 3),

          ([],0),

          ([{'manga_id' : 6, 'status' : -2, 'num_read_chapters' : 30, 'score' : 9, 'start_date_string' : '', 'finish_date_string' : ''},
            {'manga_id' : 1402, 'status' : 14, 'num_read_chapters' : 13, 'score' : 6, 'start_date_string' : '11-25-21', 'finish_date_string' : '11-25-26'},],0)
        ]
    )
    def test_create_manga_interraction_entries(self, scp_db, data, expected_added):
        n_entries = len(scp_db.cursor.execute("SELECT * FROM entries").fetchall())
        scp_db.create_manga_interraction_entries(data, 3)
        scp_db.conn.commit()
        new_n_entries = len(scp_db.cursor.execute("SELECT * FROM entries").fetchall())
        n_added = new_n_entries - n_entries
        assert expected_added == n_added
    
    def test_fetch_manga_list(self, scp_db):
        n_entries = len(scp_db.cursor.execute("SELECT * FROM entries").fetchall())

        json_path = "scraper/tests/fixtures/load.json"
        with open(json_path) as json_data:
            data = [json.load(json_data)]

        expected = len(data[0])
        with patch.object(scp_db, "collect_manga_data", return_value=data) as mock_fetch_data :
            scp_db.fetch_manga_list(name="Matmath", userid=14, n_entry=expected, sleep_time=0)
            scp_db.conn.commit()

        new_n_entries = len(scp_db.cursor.execute("SELECT * FROM entries").fetchall())
        n_added = new_n_entries - n_entries
        assert expected == n_added
    
    def test_load_from_previous_session(self, scp_db):
        n_users = scp_db.load_from_previous_session()

        assert n_users == 10 #Hardcoded variable, tbm
        assert scp_db.seen == set(["User0", "User1", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"])
        assert scp_db.added == set(["User0", "User1", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"])
    
    def test_load_pending(self, scp_db):
        scp_db.load_pending()

        assert scp_db.name_queue.qsize() == 0
        assert scp_db.seen == set()
    
    def test_load_pending_non_empty(self, scp_db):
        scp_db.cursor.execute("""INSERT INTO pending_recovery (username) VALUES (?)""", ("User10",))
        scp_db.conn.commit()

        scp_db.load_pending()
        assert scp_db.name_queue.qsize() == 1
        assert scp_db.seen == set(["User10"])
        assert scp_db.name_queue.get() == "User10"
    
    @pytest.mark.parametrize(
        "user_to_add, n_expected_pending",
        [(["User100", "User100", "User100", "User100"],1),
         ([],0),
         (["User100", "User110", "User120", "User130"],4)
        ]
    )
    def test_dump_pending_non_empty(self, scp_db, user_to_add, n_expected_pending):
        if user_to_add != []:
            for user in user_to_add:
                scp_db.name_queue.put(user)

        scp_db.dump_pending()
        n_pending = scp_db.cursor.execute("SELECT COUNT(username) FROM pending_recovery").fetchone()[0]
        usernames = [user[0] for user in scp_db.cursor.execute("SELECT * FROM pending_recovery").fetchall()]
        
        assert n_pending == n_expected_pending
        assert set(usernames) == set(user_to_add)

    def test_dump_pending_error(self, scp_db):
        scp_db.cursor = MagicMock()
        scp_db.cursor.executemany.side_effect=sqlite3.IntegrityError()
        with pytest.raises(sqlite3.IntegrityError):
            scp_db.dump_pending()
        
    @pytest.mark.parametrize("error", [None, requests.exceptions.ConnectionError,requests.exceptions.Timeout, make_http_error(403), make_http_error(429)])
    def test_integrate_user(self,error, scp_db):
        data_path = "scraper/tests/fixtures/load.json"
        call_count = 0
        with open(data_path) as f:
            data = json.load(f)
        
        scp_db.seen = set(["User0", "User1", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"])
        scp_db.added = set(["User0", "User1", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"])
        user_data = {"username" : "Matmath", "gender" : None, "birthday" : None, "location" : None, "entries" : 127, "friends" : ["User1", "User999"]}

        def fake_fetch(name, sleep_time=0):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return user_data
            if error != None:
                raise error
            else:
                return user_data

        scp_db 
        with patch.object(scp_db, "fetch_manga_profile", side_effect=fake_fetch) as mock_collect, \
            patch.object(scp_db, "collect_manga_data", return_value=[data]) as mock_fetch_profile:
            
            nb_users = scp_db.cursor.execute("SELECT COUNT(username) FROM users").fetchone()[0]
            nb_entries = scp_db.cursor.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            nb_relationships = scp_db.cursor.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]

            scp_db.integrate_user(user_data["username"], sleep_time=0)

        new_nb_users = scp_db.cursor.execute("SELECT COUNT(username) FROM users").fetchone()[0]
        new_nb_entries = scp_db.cursor.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        new_nb_relationships = scp_db.cursor.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        user_db_data = scp_db.cursor.execute("SELECT * FROM users WHERE username = ?", (user_data['username'],)).fetchone()
        user_data_keys = list(user_data.keys())
        
        new_user_id = scp_db.cursor.execute("SELECT user_id FROM users WHERE username = ?", ("Matmath",)).fetchone()[0]
        friend_id = scp_db.cursor.execute("SELECT user_id FROM users WHERE username = ?", ("User1",)).fetchone()[0]

        expected_relationship = (min(new_user_id, friend_id), max(new_user_id, friend_id))

        db_relationship = scp_db.cursor.execute("SELECT * FROM relationships").fetchone()[0]
        friend_test_id = scp_db.cursor.execute("SELECT user_id_left FROM relationships").fetchone()[0]

        if error is not None :
            assert call_count == 2
            mock_fetch_profile.assert_called_once
        else :
            mock_fetch_profile.assert_called_once
            mock_collect.assert_called_once

        assert user_data["username"] == user_db_data[1]
        assert user_data["gender"] == user_db_data[2]
        assert user_data["birthday"] == user_db_data[3]
        assert user_data["location"] == user_db_data[4]
        assert user_data["entries"] == user_db_data[5]
        assert "Matmath" in scp_db.added
        assert "User999" in scp_db.seen 
        assert "User999" not in scp_db.added
        assert (new_nb_users - nb_users == 1)
        assert (new_nb_entries - nb_entries == 127)
        assert (new_nb_relationships - nb_relationships == 1)
    
    @pytest.mark.parametrize("error", [scp.HTMLParsingException, scp.ScarceDataException, scp.PrivateListException, TypeError,MemoryError, make_http_error(404), sqlite3.IntegrityError])
    def test_abort_skip_error_integrate_user(self, error, scp_db):
        call_count = 0
        
        skip_errors = [scp.HTMLParsingException, scp.ScarceDataException, scp.PrivateListException]
        def fake_fetch(name, sleep_time=0):
            nonlocal call_count
            call_count += 1
            raise error

        with patch("time.sleep") as mock_sleep, \
            patch.object(scp_db, "fetch_manga_profile", side_effect=fake_fetch) as mock_fetch_manga_profile, \
            patch.object(scp_db, "fetch_manga_list") as mock_fetch_manga_list:
            exception = error if type(error) == type else type(error)
            if exception not in skip_errors :
                with pytest.raises(exception):
                    scp_db.integrate_user("random_name")
            else:
                scp_db.integrate_user("random_name")

        mock_fetch_manga_profile.assert_called_once
        mock_sleep.assert_called_once
        assert not mock_fetch_manga_list.called

    def test_create_users(self, scp_db):
        call_count = 0
        
        def fake_fetch(sleep_time):
            nonlocal call_count #can also be replaced by a dict according to python's assignement sorcery
            call_count += 1
            if call_count == 1:
                return ["User14", "User15"]
            else:
                scp_db.thread_A_stop_signal.set()
                return ["User1", "User450"]
        
        scp_db.seen = set(["User0", "User1", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"])
        scp_db.added = set(["User0", "User1", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"])
        scp_db.user_page_sleep = 0

        scp_db.fetch_user_page = MagicMock(side_effect=fake_fetch)
        scp_db.create_users(len(scp_db.seen))

        qsize = scp_db.name_queue.qsize()
        names = []
        for i in range(qsize):
            names.append(scp_db.name_queue.get())

        assert set(names) == set(["User14", "User15", "User450", scp_db.SENTINEL])
        assert call_count == 2
        assert "User14" in scp_db.seen
        assert "User15" in scp_db.seen
        assert "User450" in scp_db.seen

    @pytest.mark.parametrize("error,expected_sleep_var",
                             [(requests.exceptions.ConnectionError,'CONNECTION_ISSUES_SLEEP'),
                              (requests.exceptions.Timeout,'CONNECTION_ISSUES_SLEEP'),
                              (make_http_error(429),'RATE_LIMIT_SLEEP'),
                              (make_http_error(403),'RATE_LIMIT_SLEEP') ] 
                            )
    def test_connection_error_create_users(self, error, expected_sleep_var, scp_db):
        call_count = 0

        def fake_fetch(sleep_time=0):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise error
            else:
                scp_db.thread_A_stop_signal.set()
                return ["User1", "User450"]
        
        scp_db.seen = set(["User0", "User1", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"])
        scp_db.added = set(["User0", "User1", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"])
        scp_db.user_page_sleep = 0

        scp_db.fetch_user_page = MagicMock(side_effect=fake_fetch)
        with patch("time.sleep") as mock_sleep:
            scp_db.create_users(len(scp_db.seen))

        qsize = scp_db.name_queue.qsize()
        names = []
        for i in range(qsize):
            names.append(scp_db.name_queue.get())

        mock_sleep.assert_called_once_with(scp_db.params[expected_sleep_var])
        assert set(names) == set(["User450", scp_db.SENTINEL])
        assert "User450" in scp_db.seen
        assert call_count == 2
    
    @pytest.mark.parametrize("error", [make_http_error(507), TypeError])
    def test_unhandled_connection_error_create_users(self, error, scp_db):
        call_count = 0

        def fake_fetch(sleep_time):
            nonlocal call_count
            call_count += 1
            raise error
        
        scp_db.fetch_user_page = MagicMock(side_effect=fake_fetch)

        exception = error if type(error) == type else type(error) # HTTP Error are created using a method -> Instance, we need to get the type.
        with pytest.raises(exception):
            scp_db.create_users(0)
        
        assert call_count == 1
        assert scp_db.name_queue.qsize() == 1
        assert scp_db.name_queue.get() == scp_db.SENTINEL

    def test_limit_create_users(self, scp_db):
        scp_db.added = set(["User0", "User1", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"])
        scp_db.fetch_user_page = MagicMock()
        scp_db.params["MAX_USERS"] = 0
        with patch.object(scp_db, "fetch_user_page") as mock_fetch_user:
            scp_db.create_users(len(scp_db.added))

        names = []
        qsize = scp_db.name_queue.qsize() 
        for i in range(qsize):
            names.append(scp_db.name_queue.get())
        assert set(names) == set([scp_db.SENTINEL])
        assert not mock_fetch_user.called
    
    def test_empty_queue_link_user_data(self, scp_db):
        with patch.object(scp_db, "integrate_user") as mock_integrate_user, \
            patch.object(scp_db, "user_page_sleep") as mock_user_page_sleep:
            scp_db.link_user_data(0)
        
        assert not mock_integrate_user.called
        assert not mock_user_page_sleep.called
        assert scp_db.name_queue.empty()
        assert scp_db.thread_A_stop_signal.is_set()

    def test_stop_link_user_data(self, scp_db):
        scp_db.name_queue.put(scp_db.SENTINEL)
        with patch.object(scp_db, "integrate_user") as mock_integrate_user, \
            patch.object(scp_db, "compute_dynamic_sleep") as mock_compute_dynamic_sleep:
            scp_db.link_user_data(0)

        nb_pending = scp_db.cursor.execute("SELECT COUNT(*) FROM pending_recovery").fetchone()[0]

        assert nb_pending == 0
        assert not mock_integrate_user.called
        assert mock_compute_dynamic_sleep.assert_called_once
        assert scp_db.name_queue.empty()
        assert scp_db.thread_A_stop_signal.is_set()
    

    # TODO : Change the scraper mock object to avoid creating a db (and gaining some time.)
    @pytest.mark.parametrize("error",
                             [requests.exceptions.ConnectionError,
                              requests.exceptions.Timeout,
                              make_http_error(514),
                              sqlite3.IntegrityError,
                              TypeError] 
                            )
    def test_error_link_user_data(self, error, scp_db):
        call_count = 0
        scp_db.name_queue.put("User15")
        scp_db.name_queue.put("user16")
        scp_db.name_queue.put(scp_db.SENTINEL)
        def fake_fetch(sleep_time=0):
            nonlocal call_count
            call_count += 1
            raise error

        scp_db.integrate_user = MagicMock(side_effect=fake_fetch)

        with patch.object(scp_db, "dump_pending") as mock_dump_pending:
            exception = error if type(error) == type else type(error) # HTTP Error are created using a method -> Instance, we need to get the type.
            with pytest.raises(exception):
                scp_db.link_user_data(0)

        assert call_count == 1 # the other exceptions are caught and raised when they can compromise the process.
        assert not scp_db.name_queue.empty()
        assert mock_dump_pending.assert_called_once
        assert scp_db.thread_A_stop_signal.is_set()