import sys

sys.stdout.reconfigure(encoding="utf-8")

# jpholidayインストール確認
try:
    import jpholiday

    print("jpholiday: installed")
except ImportError:
    print("jpholiday: NOT installed")

# matching_v2.pyの実装状況
with open("matching_v2/matching_v2.py", encoding="utf-8") as f:
    mv2 = f.read()
print("get_min_gross実装:", "get_min_gross" in mv2)
print("evaluate_candidateでget_min_gross使用:", "get_min_gross" in mv2 and "evaluate_candidate" in mv2)
print("jpholiday in matching_v2:", "jpholiday" in mv2)
print("is_within_business_days in matching_v2:", "is_within_business_days" in mv2)

# mail_pipeline.pyの実装状況
with open("mail_pipeline/mail_pipeline.py", encoding="utf-8") as f:
    mp = f.read()
print("jpholiday in mail_pipeline:", "jpholiday" in mp)
print("is_within_business_days in mail_pipeline:", "is_within_business_days" in mp)
print("interview_datetime in mail_pipeline:", "interview_datetime" in mp)
