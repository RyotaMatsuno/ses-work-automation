# GPT Wall-Hit: Matching "No Match" Problem
Date: 2026-06-19
Model: gpt-5.4

## Root Causes (confirmed)
1. gross > 15 filter excludes projects with high/dirty price data
2. Skill matching uses exact set membership - "Java" won't match "java" or "Java/Spring"  
3. 45% of projects have no price, 58% have no required_skills
4. Price data has anomalies (0.16万, 870万 = parsing errors)

## Fix Priority
P0: Remove gross > 15 hard filter → demote to score penalty
P0: Add skill normalization (lowercase, NFKC, alias dict)
P1: Treat price=None as unknown (not zero)
P1: Add exclusion reason logging
P2: Minimum candidate guarantee (top 10 regardless)
P2: Common matching module (webhook + matching_v3)

## Target: webhook_server.py (Cloud Run) first
