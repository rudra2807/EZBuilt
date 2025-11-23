# # Path to your schema JSON
# $schemaFile = "D:\Projects\terraform-demo\schema2.json"

# # Load and parse the JSON file
# try {
#     $schemaContent = Get-Content -Path $schemaFile -Raw
#     $schemaObj = $schemaContent | ConvertFrom-Json
# } catch {
#     Write-Error "Failed to load or parse schema file at '$schemaFile'"
#     exit 1
# }

# if (-not $schemaObj.provider_schemas) {
#     Write-Error "No 'provider_schemas' object found in JSON."
#     exit 1
# }

# # **Explicitly declare** the provider key to target
# $providerKey = "data_source_schemas"

# if (-not $schemaObj.provider_schemas.Keys.Contains($providerKey)) {
#     Write-Error "Provider key '$providerKey' not found in provider_schemas."
#     Write-Host "Found keys: " + ($schemaObj.provider_schemas.Keys -join ", ")
#     exit 1
# }

# $providerSection = $schemaObj.provider_schemas.$providerKey

# if (-not $providerSection.data_source_schemas) {
#     Write-Error "No 'data_source_schemas' section found under provider key '$providerKey'."
#     exit 1
# }

# $dsKeys = $providerSection.data_source_schemas.Keys
# Write-Host "Found $($dsKeys.Count) data sources under provider key '$providerKey'."

# $outFileName = "data_sources_list_$($providerKey -replace '[\/:]', '_').txt"
# $dsKeys | Sort-Object | Out-File -FilePath $outFileName -Encoding UTF8
# Write-Host "Saved list to file: $outFileName"
$schemaObj = Get-Content -Path "D:\Projects\terraform-demo\schema2.json" -Raw | ConvertFrom-Json
$schemaObj.provider_schemas.Keys | ForEach-Object { Write-Host $_ }
