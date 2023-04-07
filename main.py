import httpx
from typing import Literal, Any
from constants import *
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/recommendations")
async def get_recommendations(user: str, include_planned: bool, media_type: Literal["ANIME", "MANGA"]) -> list[str] | None:
    
    client = httpx.AsyncClient()
    
    req_data = await client.post("https://graphql.anilist.co/", json={"query": QUERY_LIST, "variables": {"username": user, "type": media_type}})

    if not req_data:
        print("Cannot fetch provided users profile")
        return JSONResponse([], status_code=422)

    data = req_data.json()["data"]["MediaListCollection"]["lists"]

    user_series_rating_weighted = {}
    genres_ratings = {}
    to_skip = set()

    for list_data in data:
        for entry in list_data["entries"]:
            
            sid = entry["media"]["id"]
            if entry["score"] == 0:
                user_series_rating_weighted[sid] = 0.5
            else:
                for genre in entry["media"]["genres"]:
                    if genre not in genres_ratings:
                        genres_ratings[genre] = [0, 0] # (rating sum, rating count)
                    else:
                        genres_ratings[genre][0] += entry["score"]/100
                        genres_ratings[genre][1] += 1
                user_series_rating_weighted[sid] = entry["score"]/100
            if entry["status"] == "CURRENT":
                user_series_rating_weighted[sid] *= 0.75
            elif entry["status"] == "DROPPED":
                user_series_rating_weighted[sid] *= 0.25
            elif entry["status"] == "PAUSED":
                user_series_rating_weighted[sid] *= 0.5
            if entry["repeat"] != 0:
                user_series_rating_weighted[sid] *= 1 + 0.25 * entry["repeat"]
            
            if include_planned:
                if entry["status"] != "PLANNING":
                    to_skip.add(sid)
            else:
                to_skip.add(sid)

    for k in user_series_rating_weighted.keys():
        user_series_rating_weighted[k] -= 0.25
    series_ids = list(user_series_rating_weighted.keys())

    i = 0
    recommendations = {}
    while i < len(series_ids):
        id_pack = series_ids[i:i+50]

        try:
            req_recom = await client.post("https://graphql.anilist.co/", json={"query": QUERY_RECOM, "variables": {"ids": id_pack}})
        except:
            req_recom = None
            tries_left = 5
            while tries_left:
                print(f"Cannot fetch page of media data. {tries_left} tries left.")
                try:
                    req_recom = await client.post("https://graphql.anilist.co/", json={"query": QUERY_RECOM, "variables": {"ids": id_pack}})
                except:
                    pass
                if req_recom:
                    break
                tries_left -= 1
            if not req_recom:
                print("Cannot fetch page of media data. Limit reached.")
                return JSONResponse([], status_code=422)
        

        media = req_recom.json()["data"]["Page"]["media"]
        for recoms in media:
            rating_sum = sum([recom["rating"] for recom in recoms["recommendations"]["nodes"]])
            for recom in recoms["recommendations"]["nodes"]:
                if not recom:
                    continue
                if not recom["mediaRecommendation"]:
                    continue
                media_id = recom["mediaRecommendation"]["id"]
                if media_id not in recommendations:
                    recommendations[media_id] = 0
                if rating_sum:
                    recommendations[media_id] += ((recom["rating"] / rating_sum) *
                                                   user_series_rating_weighted[recoms["id"]] * 0.4 +
                                                   (recom["rating"] / rating_sum) * 0.6 *
                                                   sum([genres_ratings[genre][0]/genres_ratings[genre][1] for genre in recom["mediaRecommendation"]["genres"] if genre in genres_ratings and genres_ratings[genre][1] != 0]) 
                                                )
        
        i += 50

    recommended = []
    for rec in recommendations.keys():
        if rec not in to_skip:
            recommended.append(rec)
    recommended.sort(key=lambda x: recommendations[x], reverse=True)

    try:
        req_final = await client.post("https://graphql.anilist.co/", json={"query": QUERY_FINAL, "variables": {"ids": recommended[:10]}})
    except:
        req_final = None
        tries_left = 5
        while tries_left:
            print(f"Cannot fetch recommended series data. {tries_left} tries left.")
            try:
                req_final = await client.post("https://graphql.anilist.co/", json={"query": QUERY_RECOM, "variables": {"ids": id_pack}})
            except:
                pass
            if req_final:
                break
            tries_left -= 1
        print("Cannot fetch page of media data. Limit reached.")
        return JSONResponse([], status_code=422)
        
    final_data = req_final.json()["data"]["Page"]["media"]
    final_recoms = {}
    for recom in final_data:
        final_recoms[recom["id"]] = [recom["id"], recom["title"]["romaji"], recom["coverImage"]["large"]]

    return JSONResponse([final_recoms[ser_id] for ser_id in recommended[:10]])
        
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
    # main()
    pass