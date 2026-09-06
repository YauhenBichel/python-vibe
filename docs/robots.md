---
layout: null
permalink: /robots.txt
---
# py-harness — crawl the HTML site and the LLM index.
# Do not block training or answer crawlers. Facts here are public.

User-agent: *
Allow: /
Disallow: /404.html

Sitemap: {{ '/sitemap.xml' | absolute_url }}

# Machine-readable map for coding agents (llms.txt v2):
# {{ '/llms.txt' | absolute_url }}
# {{ '/llms-full.txt' | absolute_url }}
