import requests
from typing import Literal, Any

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
                    title { 
                        romaji
                    }
                }
            }
        }
    }
}
""".replace("    ", "")

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
""".replace("    ", "")

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
""".replace("    ", "")

def get_user_media_list(user: str, media_type: Literal["ANIME", "MANGA"]) -> list[dict[str, Any]] | None:
    req_data = requests.post("https://graphql.anilist.co/", json={"query": query_list, "variables": {"username": user, "type": media_type}})

    if not req_data:
        return None

    return req_data.json()["data"]["MediaListCollection"]["lists"]


def get_recommendations(user: str, include_planned: bool, media_type: Literal["ANIME", "MANGA"]) -> list[str] | None:
    
    data = get_user_media_list(user, media_type)
    if data is None:
        print("Cannot fetch provided users profile")
        return

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
            
            if include_planned:
                if entry["status"] != "PLANNING":
                    to_skip.add(sid)
            else:
                to_skip.add(sid)


    series_ids = list(series.keys())

    i = 0
    recommendations = {}
    while i < len(series_ids):
        id_pack = series_ids[i:i+50]

        try:
            req_recom = requests.post("https://graphql.anilist.co/", json={"query": query_recom, "variables": {"ids": id_pack}})
        except:
            req_recom = None
            tries_left = 5
            while tries_left:
                print(f"Cannot fetch page of media data. {tries_left} tries left.")
                try:
                    req_recom = requests.post("https://graphql.anilist.co/", json={"query": query_recom, "variables": {"ids": id_pack}})
                except:
                    pass
                if req_recom:
                    break
                tries_left -= 1
            print("Cannot fetch page of media data. Limit reached.")
            return
        

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

    try:
        req_final = requests.post("https://graphql.anilist.co/", json={"query": query_final, "variables": {"ids": recommended[:10]}})
    except:
        req_final = None
        tries_left = 5
        while tries_left:
            print(f"Cannot fetch recommended series data. {tries_left} tries left.")
            try:
                req_final = requests.post("https://graphql.anilist.co/", json={"query": query_recom, "variables": {"ids": id_pack}})
            except:
                pass
            if req_final:
                break
            tries_left -= 1
        print("Cannot fetch page of media data. Limit reached.")
        return
        
    final_data = req_final.json()["data"]["Page"]["media"]
    final_recoms = {}
    for recom in final_data:
        final_recoms[recom["id"]] = recom["title"]["romaji"]

    return [final_recoms[ser_id] for ser_id in recommended[:10]]
        
def main():
    while True:
        username = input("User to check: ")
        planned = input("Include series from plan to watch list? (y/n) ")
        media_type = input("Recommendation type (ANIME/MANGA): ")
        if media_type.upper() not in {"ANIME", "MANGA"}:
            print("Invalid media type provided")
            continue
        if username:
            recommendations = get_recommendations(username, planned.lower() == "y", media_type.upper())
            if recommendations is not None:
                print(f"\nRecommendations for {username}:")
                for i, recom in enumerate(recommendations, start=1):
                    print(f"{i:>2}. {recom}")
                print()
            
if __name__ == "__main__":
    main()