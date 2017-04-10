import requests

BASEURL = 'http://localhost:8000'

def test_root(server, preload):
    resp = requests.get(f'{BASEURL}/')
    assert resp.status_code == 200

def test_animal_get(server, preload):
    resp = requests.get(f'{BASEURL}/animals/cow')
    assert resp.status_code == 200
    assert resp.text == 'moo'

def test_animal_put_farmer(server, preload):
    resp = requests.get(f'{BASEURL}/animals/snake')
    assert resp.status_code == 404

    resp = requests.put(
        f'{BASEURL}/animals/snake',
        auth=('farmer', '12345'),
        data='hiss'
    )
    assert resp.status_code == 201

    resp = requests.get(f'{BASEURL}/animals/snake')
    assert resp.status_code == 200
    assert resp.text == 'hiss'
