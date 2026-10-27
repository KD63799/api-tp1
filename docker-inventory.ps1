#Requires -Version 7.4
<# TP1 — Inventaire des conteneurs via l'API Docker Engine (socket Unix).
   Sorties : inventaire-ps.csv et inventaire-ps.json #>
$ErrorActionPreference = 'Stop'
$Socket = [System.Net.Sockets.UnixDomainSocketEndPoint]::new('/var/run/docker.sock')
$Base = 'http://localhost/v1.52'

try {
    $containers = Invoke-RestMethod -UnixSocket $Socket -Uri "$Base/containers/json?all=true"
}
catch [Microsoft.PowerShell.Commands.HttpResponseException] {
    Write-Error "API Docker : HTTP $($_.Exception.Response.StatusCode.value__) — $($_.ErrorDetails.Message)"
    exit 1
}
catch {
    Write-Error "Démon Docker injoignable sur /var/run/docker.sock : $($_.Exception.Message)"
    exit 2
}

$inventaire = foreach ($c in $containers) {
    [pscustomobject]@{
        Nom    = $c.Names[0].TrimStart('/')
        Id     = $c.Id.Substring(0, 12)
        Image  = $c.Image
        Etat   = $c.State
        Statut = $c.Status
        Ports  = ($c.Ports | ForEach-Object {
            if ($_.PublicPort) { "$($_.IP):$($_.PublicPort)->$($_.PrivatePort)/$($_.Type)" }
            else { "$($_.PrivatePort)/$($_.Type)" }
        } | Sort-Object -Unique) -join ', '
    }
}

$inventaire | Format-Table -AutoSize
$inventaire | Export-Csv -Path inventaire-ps.csv -NoTypeInformation -Encoding utf8
$inventaire | ConvertTo-Json | Set-Content inventaire-ps.json -Encoding utf8
Write-Host "$($inventaire.Count) conteneur(s) → inventaire-ps.csv / inventaire-ps.json"
