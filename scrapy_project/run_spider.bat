@echo off
REM Usage: run_spider.bat <spider> <start_url>
REM Example: run_spider.bat reklama5 "https://reklama5.mk/oglasi/tehnika"
if "%1"=="" (
  echo Provide spider name (reklama5 or pazar3) as first arg
  exit /b 1
)
set SPIDER=%1
set START_URL=%2
if "%START_URL%"=="" (
  echo No start_url provided — spider will use its default start_urls
  scrapy crawl %SPIDER%
) else (
  scrapy crawl %SPIDER% -a start_url="%START_URL%"
)
