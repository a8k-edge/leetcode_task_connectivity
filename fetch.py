import asyncio
import json
import os

from aiohttp import ClientSession
import aiofiles
import requests

from conf import QUESTIONS, SIMILARS_DIR


semaphore = asyncio.Semaphore(10)


async def main():
    if not os.path.exists(SIMILARS_DIR):
        os.makedirs(SIMILARS_DIR)
    
    fetch_and_save_questions()
    await fetch_and_save_similar_qs()


def fetch_and_save_questions():
    print('FETCHING QUESTIONS')
    if os.path.isfile(QUESTIONS):
        print('Questions already exist')
        return
    headers = {
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'sec-ch-ua-mobile': '?0',
        'authorization': '',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'content-type': 'application/json',
        'uuuserid': 'd8120d74c3978738dfdff8d81584a127',
        'random-uuid': 'cf47464d-280e-959c-4fb7-7e22f1382fff',
        'Referer': 'https://leetcode.com/problemset/all/?page=1',
        'x-csrftoken': 'KGI0dqHh17BXpkiWIDIfIpQVtefmIzS2OMMRwfA42wsjZQknlndPCdhGZIR7LQSD',
        'sec-ch-ua-platform': '"Windows"',
    }

    json_data = {
        'query': '\n    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {\n  problemsetQuestionList: questionList(\n    categorySlug: $categorySlug\n    limit: $limit\n    skip: $skip\n    filters: $filters\n  ) {\n    total: totalNum\n    questions: data {\n      acRate\n      difficulty\n      freqBar\n      frontendQuestionId: questionFrontendId\n      isFavor\n      paidOnly: isPaidOnly\n      status\n      title\n      titleSlug\n      topicTags {\n        name\n        id\n        slug\n      }\n      hasSolution\n      hasVideoSolution\n    }\n  }\n}\n    ',
        'variables': {
            'categorySlug': '',
            'skip': 0,
            'limit': 2852,
            'filters': {},
        },
        'operationName': 'problemsetQuestionList',
    }
    response = requests.post('https://leetcode.com/graphql/', headers=headers, json=json_data)
    print('Fetch questions')
    data = response.json()
    print('Saving questions')
    with open(QUESTIONS, 'w') as f:
        json.dump(data['data']['problemsetQuestionList']['questions'], f)
    print('Saved questions')


async def fetch_and_save_similar_qs():
    print('FETCHING SIMILAR QUESTIONS')
    questions = []
    with open(QUESTIONS, 'r') as f:
        questions = json.load(f)

    total = len(questions)
    async with ClientSession() as session:
        tasks = [fetch_and_save_similar_q(session, q['titleSlug'], i+1, total) for i, q in enumerate(questions)]
        await asyncio.gather(*tasks)


async def fetch_and_save_similar_q(session, q_slug, current, total):
    fname = q_slug + '.json'
    if os.path.isfile(os.path.join(SIMILARS_DIR, fname)):
        print(f'Similar question {q_slug} already exist')
        return

    cookies = {
        'csrftoken': 'KGI0dqHh17BXpkiWIDIfIpQVtefmIzS2OMMRwfA42wsjZQknlndPCdhGZIR7LQSD',
    }

    headers = {
        'authority': 'leetcode.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7,fr;q=0.6,uk;q=0.5,ar;q=0.4,de;q=0.3',
        'authorization': '',
        'baggage': 'sentry-environment=production,sentry-release=0eddeea5,sentry-transaction=%2Fproblems%2F%5Bslug%5D%2F%5B%5B...tab%5D%5D,sentry-public_key=2a051f9838e2450fbdd5a77eb62cc83c,sentry-trace_id=3d67511d54924c17b59e5c642a2c5a3b,sentry-sample_rate=0.03',
        'content-type': 'application/json',
        # 'cookie': 'gr_user_id=cb1f03a1-6c24-4982-8b3e-98a179eab6cf; __stripe_mid=72b981bb-2820-4995-85d5-8e49bc2c7d060cdada; 87b5a3c3f1a55520_gr_last_sent_cs1=user3025gD; csrftoken=KGI0dqHh17BXpkiWIDIfIpQVtefmIzS2OMMRwfA42wsjZQknlndPCdhGZIR7LQSD; _ga_CDRWKZTDEX=deleted; _gid=GA1.2.1074311922.1694205316; LEETCODE_SESSION=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJfYXV0aF91c2VyX2lkIjoiOTE1MTk4NCIsIl9hdXRoX3VzZXJfYmFja2VuZCI6ImFsbGF1dGguYWNjb3VudC5hdXRoX2JhY2tlbmRzLkF1dGhlbnRpY2F0aW9uQmFja2VuZCIsIl9hdXRoX3VzZXJfaGFzaCI6IjI4MmVhNGIyY2ExZTM3ZTMxNzBlNDE4ZTNkZGJmZGRmOWQxMWI3ODQiLCJpZCI6OTE1MTk4NCwiZW1haWwiOiJzZWNvbmRhcnkuMjM0NjdAZ21haWwuY29tIiwidXNlcm5hbWUiOiJ1c2VyMzAyNWdEIiwidXNlcl9zbHVnIjoidXNlcjMwMjVnRCIsImF2YXRhciI6Imh0dHBzOi8vYXNzZXRzLmxlZXRjb2RlLmNvbS91c2Vycy9hdmF0YXJzL2F2YXRhcl8xNjgwMDg3NzAzLnBuZyIsInJlZnJlc2hlZF9hdCI6MTY5NDU5MzAwNiwiaXAiOiI5MS4yNDIuMTkzLjE0MCIsImlkZW50aXR5IjoiYzJlODc3MGE1N2JiMDVmMDJmYTk5ZmMxMDIzN2E1MTEiLCJzZXNzaW9uX2lkIjozOTU0MjkyOX0._6WNJArD2gy3gnNzLBVj1SykfacCiaOxncuN8yZiW7k; 87b5a3c3f1a55520_gr_session_id=b7140fda-ebc5-407f-8227-8c1474db0580; 87b5a3c3f1a55520_gr_last_sent_sid_with_cs1=b7140fda-ebc5-407f-8227-8c1474db0580; 87b5a3c3f1a55520_gr_session_id_sent_vst=b7140fda-ebc5-407f-8227-8c1474db0580; _gat=1; _dd_s=rum=0&expire=1694679563563; 87b5a3c3f1a55520_gr_cs1=user3025gD; _ga=GA1.1.1154511274.1678650048; _ga_CDRWKZTDEX=GS1.1.1694677567.92.1.1694678663.44.0.0',
        'origin': 'https://leetcode.com',
        'random-uuid': 'cf37464d-280e-959c-4fb3-7e27f1382fcf',
        'referer': 'https://leetcode.com/problems/two-sum/',
        'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Google Chrome";v="116"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sentry-trace': '3d67511d54924c17b59e5c642a2c5a3b-b7d1869911e871a8-0',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'uuuserid': 'd8120d74c3978738dfdff8d81584a127',
        'x-csrftoken': 'KGI0dqHh17BXpkiWIDIfIpQVtefmIzS2OMMRwfA42wsjZQknlndPCdhGZIR7LQSD',
    }

    json_data = {
        'query': '\n    query SimilarQuestions($titleSlug: String!) {\n  question(titleSlug: $titleSlug) {\n    similarQuestionList {\n      difficulty\n      titleSlug\n      title\n      translatedTitle\n      isPaidOnly\n    }\n  }\n}\n    ',
        'variables': {
            'titleSlug': q_slug,
        },
        'operationName': 'SimilarQuestions',
    }

    async with semaphore:
        async with session.post('https://leetcode.com/graphql/', cookies=cookies, headers=headers, json=json_data) as response:
            data = await response.json()
            async with aiofiles.open(os.path.join(SIMILARS_DIR, fname), 'w') as f:
                await f.write(json.dumps(data['data']['question']['similarQuestionList']))
            print(f"Fetched and saved {current}/{total}")


if __name__ == '__main__':
    asyncio.run(main())