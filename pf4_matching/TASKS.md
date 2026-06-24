# TASKS.md - Phase4

- [ ] 1. matching_v3.py の先頭にsys.path修正コードを追加（SPEC変更1）
- [ ] 2. matcher.py: judge() の粗利ルール修正（+15→5万床、SPEC変更2）
- [ ] 3. matcher.py: judge() の未知必須スキルREVIEW化（SPEC変更3）
- [ ] 4. matcher.py: judge() の並行スコアNG化（SPEC変更4）
- [ ] 5. notion_client.py: get_active_engineers()に提案対象フラグfilter追加（SPEC変更5）
- [ ] 6. matching_v3/cost_guard.py: get_model()のGemineデグレード除去（SPEC変更6）
- [ ] 7. pf4_matching/setup_workdir.py を作成・実行してSES_MatchingV3のWorkDirをses_workに設定（SPEC変更7）
- [ ] 8. syntax確認: `python -c "import py_compile; [py_compile.compile(f, doraise=True) for f in ['../matching_v3/matching_v3.py','../matching_v3/matcher.py','../matching_v3/notion_client.py','../matching_v3/cost_guard.py']]; print('ALL OK')"`
