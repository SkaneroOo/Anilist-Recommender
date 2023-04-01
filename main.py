import requests

query_list = """
query ($username: String, $type: MediaType) {
  MediaListCollection(userName: $username, type: $type) {
    lists {
      entries {
        status
        score(format: POINT_100)
        progress
        repeat
        media {
          id
          title { romaji }
        }
      }
    }
  }
}
"""

query_recom = """
query ($ids: [Int]) {
  Page(page: 1, perPage: 50) {
    media(id_in: $ids) {
      id
      recommendations(page: 1, perPage: 25, sort: RATING_DESC) {
        nodes{
          rating
          mediaRecommendation{
            id
          }
        }
      }
    }
  }
}
"""

query_final = """
query ($ids: [Int]) {
   Page(page: 1, perPage: 10) {
    media(id_in: $ids) {
      id,
      title {
        romaji
      },
      coverImage {
        extraLarge
      }
    }
  }
}
"""

def get_recommendations(user: str):
    req_data = requests.post("https://graphql.anilist.co/", json={"query": query_list, "variables": {"username": user, "type": "ANIME"}})

    if not req_data:
        print("AAAAAAAAAAAAAAAAA")
        exit()

    data = req_data.json()["data"]["MediaListCollection"]["lists"]

    series = {}
    to_skip = set()

    for list_data in data:
        for entry in list_data["entries"]:
            sid = entry["media"]["id"]
            if entry["score"] == 0:
                series[sid] = 0.5
            else:
                series[sid] = entry["score"]/100
            if entry["status"] == "CURRENT":
                series[sid] *= 0.75
            elif entry["status"] == "DROPPED":
                series[sid] *= 0.25
            elif entry["status"] == "PAUSED":
                series[sid] *= 0.5
            if entry["repeat"] != 0:
                series[sid] *= 1 + 0.25 * entry["repeat"]
            if entry["status"] != "PLANNING":
                to_skip.add(sid)
            # to_skip.add(sid)


    series_ids = list(series.keys())

    i = 0
    recommendations = {}
    while i < len(series_ids):
        id_pack = series_ids[i:i+50]
        req_recom = requests.post("https://graphql.anilist.co/", json={"query": query_recom, "variables": {"ids": id_pack}})
        
        if not req_recom:
            print("AAAAAAAAAAAAAAAAAAAAA")
            exit()
        
        media = req_recom.json()["data"]["Page"]["media"]
        for recoms in media:
            rating_sum = sum([recom["rating"] for recom in recoms["recommendations"]["nodes"]])
            # print(rating_sum)
            for recom in recoms["recommendations"]["nodes"]:
                if not recom:
                    continue
                if not recom["mediaRecommendation"]:
                    continue
                media_id = recom["mediaRecommendation"]["id"]
                if media_id not in recommendations:
                    recommendations[media_id] = 0
                if rating_sum:
                    recommendations[media_id] += (recom["rating"] / rating_sum) * series[recoms["id"]]
        
        i += 50

    recommended = []
    for rec in recommendations.keys():
        if rec not in to_skip:
            recommended.append(rec)
    recommended.sort(key=lambda x: recommendations[x], reverse=True)

    req_final = requests.post("https://graphql.anilist.co/", json={"query": query_final, "variables": {"ids": recommended[:10]}})

    if not req_final:
        print("AAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        exit()
        
    final_data = req_final.json()["data"]["Page"]["media"]
    final_recoms = {}
    for recom in final_data:
        final_recoms[recom["id"]] = recom["title"]["romaji"]

    for i, ser_id in enumerate(recommended[:10], start=1):
        print(f"{i}. {final_recoms[ser_id]}")
        
def main():
    while True:
        username = input("User to check: ")
        if username:
            get_recommendations(username)
            
if __name__ == "__main__":
    main()