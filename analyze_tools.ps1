$dir = "$env:USERPROFILE\.claude\projects\C--Users-ma-py-OneDrive--------ses-work"
$files = Get-ChildItem "$dir\*.jsonl" -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 50

$counts = @{}

foreach ($f in $files) {
    $lines = Get-Content $f.FullName -Encoding UTF8 -ErrorAction SilentlyContinue
    foreach ($line in $lines) {
        if (-not $line.Trim()) { continue }
        try {
            $obj = $line | ConvertFrom-Json
        } catch { continue }

        $msg = $obj.message
        if (-not $msg -or $msg.role -ne "assistant") { continue }

        foreach ($block in $msg.content) {
            if ($block.type -ne "tool_use") { continue }
            $name = $block.name

            if ($name -eq "Bash") {
                $cmd = $block.input.command
                if (-not $cmd) { continue }
                $cmd = $cmd -replace '^([A-Z_]+=\S+\s+)+', ''
                $tokens = $cmd.Trim() -split '\s+'
                if ($tokens.Count -eq 0) { continue }
                $t0 = $tokens[0]
                if ($t0 -in @('sudo','timeout') -and $tokens.Count -gt 1) {
                    $tokens = $tokens[1..($tokens.Count-1)]
                    $t0 = $tokens[0]
                }
                if ($tokens.Count -ge 2 -and $t0 -in @('git','gh','docker','kubectl','npm','pip','python','python3','pytest')) {
                    $key = "$($tokens[0]) $($tokens[1])"
                } else {
                    $key = $t0
                }
                if ($counts.ContainsKey($key)) { $counts[$key]++ } else { $counts[$key] = 1 }
            } else {
                if ($counts.ContainsKey($name)) { $counts[$name]++ } else { $counts[$name] = 1 }
            }
        }
    }
}

$counts.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 60 | ForEach-Object {
    "{0,5}  {1}" -f $_.Value, $_.Key
}
