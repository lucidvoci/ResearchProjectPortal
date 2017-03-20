#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------        Autor: Lucie Dvorakova      ----------------------#
#-------------------           Login: xdvora1f          ----------------------# 
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

import re
import sys
import math
from flask import Flask
from flask import request
from flask import render_template
from elasticsearch import Elasticsearch
from datetime import datetime
from cStringIO import StringIO
from elasticutils import get_es, S, MLT

from query import Query

HOST        = "localhost"
PORT        = 9200
IDXPROJ     = "xdvora1f_projects"
IDXDELIV    = "xdvora1f_deliverables"
DOCTYPE     = "data"
URL         = "http://%s:%d/" % (HOST, PORT)

ITEMS_PER_PAGE = 20
last_url = ''

es = Elasticsearch(host=HOST, port=PORT)
deliv_s = S().es(urls=[URL]).indexes(IDXDELIV).doctypes(DOCTYPE)
project_s = S().es(urls=[URL]).indexes(IDXPROJ).doctypes(DOCTYPE)

app = Flask(__name__)

@app.route("/")
def index():
    code = render_template("index.html")
    return code

@app.route("/find", methods=["GET"])
def find():
    global last_url
    last_url = request.url
    # search in project or deliverables (projects are default)
    search = request.args.get("search", "projects")

    # get current page, or default to zero
    try:
        page = int(request.args.get("page", "0"))
        if page < 0:
            page = 0
    except:
        page = 0
        
    # getting search query with keywords
    keyword = request.args.get("keyword", "")
    q = Query(keyword)
    #print q.keywords
    #print q.specifications

    # getting facets from url and query
    search_dic = {}
    valid_specs = ["country", "programme", "subprogramme", "coordinator",
        "participant", "year"]

    # specification from search box is prioritized 
    for spec in valid_specs:
        val = q.getSpecification(spec)
        if val:
            search_dic[spec] = val.strip().lower()
            continue

        val = request.args.get(spec)
        if val:
            search_dic[spec] = val.replace("+", " ").strip().lower()
    
    # build actual query for ElasticSearch 
    offset = page*ITEMS_PER_PAGE
    keywords = " ".join(q.getKeywords())
    keyword_s = get_project_with_keywords(keywords, search, \
        offset, offset+ITEMS_PER_PAGE)

    if len(search_dic) > 0:
        keyword_s = keyword_s.filter(**search_dic)
        
    # getting facets
    facet = facets(keyword_s)
    
    # getting instant show
    instan_s = ''
    if keyword_s:
        if keyword_s[0].es_meta.score > 3:
            instan_s = keyword_s
        else:
            filter_args = {"abbr": keyword}
            instan_s = keyword_s.filter(**filter_args)

    #if keyword deleted, no results are found
    if not keywords:
        keyword_s = ''
        instan_s = ''
        
    # if not enought project fill with deliv + create facet of projects
    deli_s = ''
    deli_facet = []
    if keyword_s:
        if keyword_s.count() < ITEMS_PER_PAGE:
            if search == 'projects':
                deli_s = get_project_with_keywords(keywords, 'deliverables', \
                    offset, offset+ITEMS_PER_PAGE)
                deli_facet = deliverable_facets(deli_s)
                deli_s = deli_s[0:ITEMS_PER_PAGE - keyword_s.count()]
    else:
        if search == 'projects':
            deli_s = get_project_with_keywords(keywords, 'deliverables', \
                offset, offset+ITEMS_PER_PAGE)
            deli_facet = deliverable_facets(deli_s)
            deli_s = deli_s[0:ITEMS_PER_PAGE]

    
    safe_keywords = re.sub(r'([:\\"])', r'\\\1', keywords)
    safe_search_dic = {}
    for key in search_dic:
        safe_key = re.sub(r'([:\\"])', r'\\\1', key)
        safe_val = re.sub(r'([:\\"])', r'\\\1', search_dic[key])
        safe_search_dic[safe_key] = safe_val

    code = render_template('find.html', keyword=safe_keywords, s=keyword_s, \
        f=facet, d=safe_search_dic, search=search, insta=instan_s, page=page, \
        deli=deli_s, deli_facet = deli_facet)
    return code

@app.route('/project/<projectid>')
def project_detail(projectid):
    global project_s
    global last_url
    
    #getting similar projects
    mlt_s = MLT(projectid, index=IDXPROJ, doctype=DOCTYPE, search_size=3)

    filter_args = {"id": projectid}
    data_s = project_s.filter(**filter_args)
    deli_s = deliv_s.filter(**filter_args)
    code = render_template('project.html', s = data_s[0], d = deli_s[0:50], url = last_url, similar=mlt_s)
    return code

@app.route('/user/')
@app.route('/user/<name>')
def user(name=None):
    return render_template('user.html', name=name)

## --------------------------------------- ##
## -------------- FUNKCE ----------------- ##
## --------------------------------------- ##

# Vrati filtr vsech projektu kde se nachazeji klicova slova
def get_project_with_keywords(keyword, search, from_, to):
    if search == 'projects':
        keyword_s = project_s.query_raw({
            "multi_match" : {
                "query" : keyword,
                "fields" : [ "abbr^6","title^5", "subprogramme^3", "objective", "origWeb"],
#                "type" : "phrase"
                }    
            })
        keyword_s = keyword_s[from_:to]
        keyword_s = keyword_s.highlight('objective', pre_tags = ["<b>"], post_tags = ["</b>"])
    else:
        keyword_s = deliv_s.query_raw({
            "multi_match" : {
                "query" : keyword,
                    "fields" : [ "deliv_title^3", "deliv_article"],
#                    "type" : "phrase"
                }
            })
        keyword_s = keyword_s[from_:to]
        keyword_s = keyword_s.highlight('deliv_article', pre_tags = ["<b>"], post_tags = ["</b>"])
    return keyword_s


# Generuje leve menu s facety na zaklade filtru facet_s
def facets(keyword_s):
    listfacet = [['programme', []], ['subprogramme', []],['year', []], ['coordinator', []], ['participant', []], ['country',[]]]
    for facet in listfacet:
        facet_s = keyword_s.facet(facet[0], filtered=True, size=20).facet_counts()
        for value in facet_s[facet[0]]['terms']:
            facet[1].append([value['term'], str(value['count'])])
    return listfacet

# finding projects with deliverables
def deliverable_facets(deli_s):
    deli_facet = []
    deli_facet_s = deli_s.facet("id", filtered=True, size=100).facet_counts()
    for item in deli_facet_s['id']['terms']:
        filter_args = {"id": item['term']}
        tmp_s = deli_s.filter(**filter_args)
        deli_facet.append([item['term'],tmp_s[0]['abbr']])
    return deli_facet


    



if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

