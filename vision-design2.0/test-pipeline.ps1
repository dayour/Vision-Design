$payload = @{
    action = "generate"
    prompt = "test image"
    model = "flux-pro"
    n = 1
    size = "1024x1024"
    response_format = "b64_json"
    save_options = @{
        enabled = $false
    }
} | ConvertTo-Json -Compress

$form = @{
    payload = $payload
}

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/images/pipeline" -Method POST -Body $form -ContentType "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW"
    Write-Host "Success: $($response.StatusCode)"
    Write-Host $response.Content
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host $_.Exception.Response.StatusCode
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    Write-Host $reader.ReadToEnd()
}
