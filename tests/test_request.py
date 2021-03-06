#!/usr/bin/env python

import asyncio

from ruia import Request
from ruia.exceptions import InvalidRequestMethod

sem = asyncio.Semaphore(3)


async def hello(response):
    return 'hello ruia'


def hi(response):
    yield 'hi ruia'


async def retry_func(request):
    request.request_config['TIMEOUT'] = 10


params = {
    "name": "ruia"
}


async def valid_response(response):
    return response


async def make_get_request(sem, callback=None):
    request_config = {
        'RETRIES': 3,
        'DELAY': 1,
        'TIMEOUT': 0.1,
        'VALID': valid_response,
        'RETRY_FUNC': retry_func
    }
    request = Request('https://httpbin.org/get',
                      method='GET',
                      metadata={'hello': 'ruia'},
                      request_config=request_config,
                      params=params,
                      callback=callback)
    return await request.fetch_callback(sem)


async def make_post_request(sem, callback):
    headers = {
        'Content-Type': 'application/json'
    }
    request = Request('https://httpbin.org/post',
                      method='POST',
                      headers=headers,
                      data=params,
                      callback=callback)
    return await request.fetch_callback(sem)


def test_request_config():
    assert str(Request('https://httpbin.org/')) == '<GET https://httpbin.org/>'
    _, response = asyncio.get_event_loop().run_until_complete(make_get_request(sem=sem, callback=hello))
    assert response.callback_result == 'hello ruia'
    assert response.metadata == {'hello': 'ruia'}
    json_result = asyncio.get_event_loop().run_until_complete(response.json())
    assert json_result['args']['name'] == "ruia"

    _, response = asyncio.get_event_loop().run_until_complete(make_post_request(sem=sem, callback=None))
    json_result = asyncio.get_event_loop().run_until_complete(response.json())
    assert json_result['data'] == "name=ruia"


def test_method_error_request():
    try:
        request = Request('https://httpbin.org/', method='PUT')
        response = asyncio.get_event_loop().run_until_complete(request.fetch())
        assert response.html == ''
    except Exception as e:
        assert isinstance(e, InvalidRequestMethod)


def test_sem_error_request():
    _, response = asyncio.get_event_loop().run_until_complete(make_get_request(sem=None, callback=None))
    assert response == None


def test_retry_request():
    request = Request('http://httpbin.org/404')
    _, response = asyncio.get_event_loop().run_until_complete(request.fetch_callback(sem=sem))
    assert response.url == 'http://httpbin.org/404'


def test_timeout_request():
    async def timeout_request(sem):
        request_config = {
            'RETRIES': 1,
            'DELAY': 1,
            'TIMEOUT': 0.1,
        }
        request = Request('https://httpbin.org/get',
                          method='GET',
                          metadata={'hello': 'ruia'},
                          encoding='utf-8',
                          request_config=request_config,
                          params=params,
                          callback=hi)
        return await request.fetch_callback(sem)

    _, response = asyncio.get_event_loop().run_until_complete(timeout_request(sem=sem))
    assert response.url == 'https://httpbin.org/get'
