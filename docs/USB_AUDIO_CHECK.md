# Test USB AUDIO reproductible (MKI / MKII)

## Quick start (English)

Close all audio clients, connect the OT running the USB audio firmware under
comparison, and keep monitor volume low. Use a disposable test project and
route A/B to monitoring manually. Requirements: Python 3, numpy, sounddevice
with native PortAudio, pyusb and native libusb matching Python's architecture.
The script does not install dependencies or change the firmware.

```sh
python3 tools/usb_audio_check.py --list-devices
python3 tools/usb_audio_check.py --unit mki --build-note 'OCTABAM96 #514 usb-io-main-cue-abcd' --connection-note 'direct USB, same cable' --output usb-check-01
```

Defaults: 3 seconds, 440 Hz, -26 dBFS, 44.1 kHz, host outputs 1/2; other
advertised outputs are silent. Use `--unit mkii` for MKII, and a fresh output
directory for each run. Share `report.json`, `samples.jsonl`, `result.txt` and
whether the tone was continuous, gated or silent. Review free-text/device
names before sharing. The runner is an independent adaptation, not a run of
upstream `usb_probe.py`/`usb_counters.py`. It was validated offline; this new
runner has not yet been tested on hardware. Existing observations used a
separate private Python runner.

Verdicts: `OBSERVED_ERRORS`, `INCONCLUSIVE`, `NO_ERROR_OBSERVED`. The last
means no error was observed during the sampled window, not proven continuous
audio. Ring counters are not completed USB byte counts; resets, re-anchors
and overflows prevent exact throughput inference. Requested/wall time is
informational. A watchdog bounds only its own child process (20 seconds for
the default test); partial data survive a timeout. It never claims/detaches a
USB interface or directly changes alternate settings. Output-only playback
may still activate duplex/implicit feedback in the host driver.

To compare hosts, keep firmware/profile, tone parameters and cable unchanged;
record OS, architecture and direct/hub connection. Stop if the unit becomes
unresponsive. Linux/Windows access/backend compatibility is unverified: do
not replace the audio driver just to obtain counters.

## Checklist (français)

Outil autonome : [`tools/usb_audio_check.py`](../tools/usb_audio_check.py).
Copier ce seul fichier suffit ; Python 3 et les dépendances **numpy,
sounddevice (PortAudio), pyusb et libusb natif**, installées pour la même
architecture que Python, doivent déjà être disponibles. Le script n’installe
rien. Intel et Apple Silicon utilisent exactement les mêmes commandes.
Sur Linux/Windows, un backend PortAudio et l’accès EP0/libusb sont nécessaires ;
ne pas remplacer/détacher le pilote audio pour obtenir les compteurs.
Ces plateformes ne sont pas validées matériellement par cet outil.

1. Noter MKI/MKII, version/image exacte et profil (témoin conseillé :
   `OCTABAM96 #514 usb-io-main-cue-abcd`, 4 entrées / 4 sorties, 44 100 Hz),
   OS, câble, direct/hub. Garder la même image/câble/paramètres sur l’autre Mac
   ou OS pour comparer ; ne changer qu’un élément à la fois.
2. Fermer manuellement Live, les autres DAW, lecteurs et applications audio.
   Le script ne ferme aucune application. Utiliser un **projet OT jetable**,
   volume d’écoute bas ; vérifier manuellement le routage des entrées A–D
   vers l’écoute/les VU. Éviter toute boucle de retour analogique.
3. Lister les périphériques ; conserver noms et nombre de canaux d’entrée
   et sortie. La fréquence par défaut affichée n’est pas celle du test :
   le flux impose 44 100 Hz. `--device` choisit une sous-chaîne unique.
4. Préflight facultatif, puis **un essai de 3 s**, sorties hôte 1/2 vers A/B.
   Le flux utilise toutes les sorties annoncées (4 pour profil 4/4), les
   autres restent à zéro. `--channels 3,4` permet ensuite un essai C/D distinct.
   Arrêter si l’unité se bloque ; ne pas prolonger un stress qui échoue.
5. Consigner à côté du rapport : son continu/haché/muet, A/B ou C/D observés,
   unité réactive ou non, application audio fermée, version libusb si connue.
   Le rapport n’enregistre **aucune entrée audio** et ne prouve pas ce routage.

Depuis la racine du dépôt public, ou depuis `octalab/` dans le dépôt de travail (adapter le chemin si le script est copié seul) :

```sh
python3 tools/usb_audio_check.py --list-devices
python3 tools/usb_audio_check.py --unit mki --build-note 'OCTABAM96 #514 usb-io-main-cue-abcd' --connection-note 'USB direct, meme cable' --output usb-check-01
```

Pour MKII : remplacer `--unit mki` par `--unit mkii`. Ajouter `--preflight`
pour recueillir périphériques, versions et un snapshot EP0 **sans ouvrir de
flux audio** (répertoire de rapport séparé). Si libusb n’est pas trouvé,
indiquer le chemin réel de sa bibliothèque installée, par exemple :

```sh
LIBUSB_LIBRARY='/chemin/reel/libusb-1.0.dylib' python3 tools/usb_audio_check.py --unit mki --build-note 'OCTABAM96 #514' --output usb-check-02
```

Ne pas donner un chemin d’une autre architecture. La checklist ne demande
aucune installation, nouveau firmware, flash ou changement global de réglage.
L’outil n’utilise aucun chemin vers un autre dépôt ni chemin macOS prédéfini.

Chaque commande de test écrit **report.json**, **samples.jsonl**, **result.txt**
dans un répertoire neuf. Le rapport inclut OS/architecture/Python,
versions des modules/PortAudio, liste de périphériques audio, capacités,
configuration négociée et identification USB VID/PID/version (sans serial,
nom utilisateur, hostname ni chemins personnels). Les champs libres et noms
personnalisés de périphériques doivent être relus avant partage.

Valeurs par défaut : 3 s, 440 Hz, -26 dBFS, 44 100 Hz, canaux 1/2.
`--duration` est bornée à 30 s. Un parent externe borne son **seul enfant**
à `max(20, durée × 2 + 10)` secondes (70 s maximum), le tue en cas de timeout
et conserve les snapshots/rapport partiels. Une fermeture de flux bloquée
reste un échec explicite ; la fin du processus ne garantit pas qu’un pilote
ou l’unité a récupéré. Le retour normal clôt explicitement le flux.
Code de retour 0 : `NO_ERROR_OBSERVED` ; 2 : erreurs, préflight ou inconclusif.

## Lecture prudente

Les GET EP0 `0x55` (OT→hôte) et `0x56` (hôte→OT) n’effectuent ni claim,
configuration, detach ni changement d’alternate setting. #514 renvoie
15 longs / 60 octets pour chacun ; le script accepte aussi le préfixe
ancien 0x55 à au moins 12 longs et les extensions 0x56 à 28 longs.
Une réponse courte/non alignée ou STALL est un diagnostic conservé,
pas un crash ni un résultat sain. Chaque requête conserve UTC, monotonic,
fin monotonic et octets hex ; aucun dump firmware ni audio capturé.

Seuls les polls entièrement entre démarrage effectif et fin observée du
flux participent aux différences ; baseline, fin chevauchée et post-close
restent séparés. Les baisses de compteurs cumulatifs sont explicitement
`reset_or_wrap`. Minfill/maxfill/lastfill/anchor sont des **états**, pas des
compteurs à soustraire. Un réancrage/overflow/reset invalide une pente de ring ;
le script ne calcule aucun débit de bus. `consumed` inclut préparation des
paquets, ancrages et sauts d’overflow : ce n’est pas des bytes USB complétés.
Le rapport durée demandée/durée hôte est informatif (démarrage, polling et
arrêt inclus), jamais un verdict « moitié du débit ».

- **OBSERVED_ERRORS** : croissance observée d’erreurs, over/underruns,
  reprimes, bankdup/srcjump, ou status callback PortAudio.
- **INCONCLUSIVE** : compteurs manquants, trop peu de polls, poll échoué,
  gros intervalle, reset/réancrage, arrêt/timeout/échec ou préflight seul.
- **NO_ERROR_OBSERVED** : aucun de ces signaux pendant la fenêtre échantillonnée.
  Cela ne prouve ni audio analogique continu, ni fiabilité longue durée.

Même output-only, le pilote peut activer un chemin duplex/implicit feedback.
Une reprise entre deux polls peut échapper aux compteurs. Les erreurs peuvent
être cause **ou conséquence** des reprises ; comparer les rapports et l’écoute,
sans attribuer automatiquement la panne au firmware ou au DAW.
