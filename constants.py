QUERY_LIST = """
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
                    genres
                }
            }
        }
    }
}
""".replace("    ", "") # reducing payload size

QUERY_RECOM = """
query ($ids: [Int]) {
    Page(page: 1, perPage: 50) {
        media(id_in: $ids) {
            id
            recommendations(page: 1, perPage: 25, sort: RATING_DESC) {
                nodes{
                    rating
                    mediaRecommendation{
                        id
                        genres
                    }
                }
            }
        }
    }
}
""".replace("    ", "")

QUERY_FINAL = """
query ($ids: [Int]) {
    Page(page: 1, perPage: 10) {
        media(id_in: $ids) {
            id,
            title {
                romaji
            },
            coverImage {
                large
            }
        }
    }
}
""".replace("    ", "")