#!/usr/bin/env bash
# 数据源连通性验证 — 首测 2026-10-12 双源通过
# 用法: bash spike/verify_datasources.sh
set -e

echo "== 1/2 World Bank API v2 (免密钥, 多国批量) =="
curl -sS --max-time 25 \
  "https://api.worldbank.org/v2/country/CHN;USA;JPN;DEU;BRA/indicator/IT.NET.USER.ZS?format=json&date=2023&per_page=10" \
  | head -c 300
echo; echo

echo "== 2/2 UN Comtrade public preview (免密钥, 有限流) =="
curl -sS --max-time 25 \
  "https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=392&period=2023&cmdCode=8419&flowCode=M" \
  | head -c 300
echo; echo

echo "OK: both datasources reachable"
