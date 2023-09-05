import requests
id=1
response=requests.get(f'https://pokeapi.co/api/v2/pokemon/{id}/')
print(response)
if response.status_code==200:
    data = response.json()
    print(data['name'])

else:
    print('error'+response.status_code)

