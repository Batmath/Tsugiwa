def fetch_user_page():

    def is_user_href(tag):
        return tag.has_attr('href') and not tag.find('img') and re.compile("/profile").search(tag['href'])
    
    target_page = "https://myanimelist.net/users.php"

    req = requests.get(target_page)
    if req.status_code == 200 :
        soup = BeautifulSoup(req.text, "html.parser")
        users = list(map(lambda x : x.text, soup.find_all(is_user_href)))
        print(users)
    else : 
        req.raise_for_status()

def fetch_user_info(name:str, base_url= "https://api.jikan.moe/v4/users"):
    req = requests.get(base_url + name)

    if req.status_code == 200:
        data = req.json()['data']
        return {'user_id' : data['mal_id'], 'username' : data['username'], 'gender' : data['gender'], 'location' : data['location']}
    else:
        req.raise_for_status()