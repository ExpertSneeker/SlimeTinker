from pathlib import Path
import sys, subprocess, zipfile, hashlib, re, json, xml.etree.ElementTree as ET
repo=Path(__file__).resolve().parents[1]
original=Path(sys.argv[1]).resolve();classpath_file=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();out.mkdir(parents=True,exist_ok=True)
expected="3fed4565fbc22ca882b1fdc2553d48cfcf1da380b7ddc1b5bc7a687731a25f3d"
if hashlib.sha256(original.read_bytes()).hexdigest()!=expected:raise SystemExit("Original JAR hash differs from reviewed baseline")
empty=out/"empty-sourcepath";empty.mkdir(exist_ok=True)
args=["sh","./mvnw","-B","-f","coreages-patch-pom.xml","-Dcoreages.classpath="+classpath_file.read_text().strip(),"-Dcoreages.output="+str(out/"compiled"),"-Dcoreages.emptySourcePath="+str(empty),"compile"]
with (out/"maven.log").open("w") as f:r=subprocess.run(args,cwd=repo,stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit("Compilation failed; inspect "+str(out/"maven.log"))
classes={str(f.relative_to(out/"compiled/classes")).replace("\\","/"):f.read_bytes() for f in (out/"compiled/classes").rglob("*.class")}
expected_classes={"io/github/sefiraat/slimetinker/"+x+".class" for x in ["events/EntityDamageEvents","listeners/EntityDamagedListener","runnables/event/KingsmanSpam"]}
if set(classes)!=expected_classes:raise SystemExit("Unexpected output classes")
version=ET.parse(repo/"pom.xml").getroot().find("{http://maven.apache.org/POM/4.0.0}version").text
if version!="coreages.20261115.dustfix":raise SystemExit("Unexpected patch version")
fixed=out/"SlimeTinker-coreages.20261115.dustfix.jar"
changed=[]
with zipfile.ZipFile(original) as src,zipfile.ZipFile(fixed,"w") as dst:
 for info in src.infolist():
  data=src.read(info.filename)
  if info.filename in classes:data=classes[info.filename]
  elif info.filename=="plugin.yml":data=re.sub(r"(?m)^version:.*$",'version: "Build 57 (git 41be204) +'+version+'"',data.decode()).encode()
  if data!=src.read(info.filename):changed.append(info.filename)
  dst.writestr(info,data)
with zipfile.ZipFile(fixed) as z:
 if z.testzip() is not None:raise SystemExit("ZIP CRC failure")
if set(changed)!=expected_classes|{"plugin.yml"}:raise SystemExit("Unexpected changed entries")
manifest={"originalSha256":expected,"fixedSha256":hashlib.sha256(fixed.read_bytes()).hexdigest(),"fixedBytes":fixed.stat().st_size,"changedEntries":changed,"version":"Build 57 (git 41be204) +"+version}
(out/"artifact.json").write_text(json.dumps(manifest,indent=2)+"\n");print(json.dumps(manifest))
