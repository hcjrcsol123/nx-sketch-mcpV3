"""Generate one narrow P2 C# fixture from validated V3 IR; never runs NX.

The generated journal embeds only finite numeric data and creates one new part.
The supported contract is deliberately narrower than the general V3 IR.
"""
import argparse
import ast
import json
import math
from pathlib import Path

from ..ir import Plan


class UnsupportedPlan(ValueError):
    """Valid IR is outside the single demonstrated fixture."""


def _reject(message):
    raise UnsupportedPlan(message)


def _finite_positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        _reject(name + " must be finite and strictly positive")
    return float(value)


def map_plan(plan, edit_x, edit_width):
    """Validate every IR construct and return explicit numeric fixture inputs."""
    if not isinstance(plan, Plan):
        _reject("expected validated V3 Plan")
    d = plan.to_dict()
    reference = d["reference"]
    if reference != {"snapshot_id": "manual_block_smoke", "path": "manual://block-smoke", "version": "manual", "selected_body": "smoke_body", "length_unit": "mm", "rigid_transform": {"origin": [0, 0, 0], "x_axis": [1, 0, 0], "y_axis": [0, 1, 0]}}:
        _reject("reference or frame outside the P2 manual block")
    if d["regions"] != [{"id": "block_region", "source_geometry": [], "confirmed": True}]:
        _reject("only the confirmed source-free block region is supported")
    expected_ops = [
        {"id":"base", "kind":"datum_plane", "depends_on":[], "region_id":"block_region", "parameters":{}, "data":{"origin":[0,0,0], "x_axis":[1,0,0], "y_axis":[0,1,0]}, "source_geometry":[], "confirmed":True},
        {"id":"profile", "kind":"sketch_rectangle", "depends_on":["base"], "region_id":"block_region", "parameters":{"x":"x", "y":"y", "width":"width", "height":"height"}, "data":{"datum_id":"base"}, "source_geometry":[], "confirmed":True},
        {"id":"block", "kind":"extrude", "depends_on":["profile"], "region_id":"block_region", "parameters":{"distance":"depth"}, "data":{"sketch_id":"profile", "boolean":"create"}, "source_geometry":[], "confirmed":True},
    ]
    if d["operations"] != expected_ops:
        _reject("operation set, order, bindings or dependencies are unsupported")
    if d["constraints"] or d["open_items"] or sorted(d["capability_requirements"]) != ["extrude_create", "rectangle_driving_dimensions"]:
        _reject("unhandled constraint, capability or open item")
    params = {p["id"]: p for p in d["parameters"]}
    if len(d["parameters"]) != 5 or set(params) != {"x", "y", "width", "height", "depth"}:
        _reject("parameter set must match the five fixture parameters")
    for p in params.values():
        if p["dimension"] != "length":
            _reject("all fixture parameters must be lengths")
    values = {}
    for key in ("x", "y", "width", "depth"):
        if params[key]["expression"] is not None:
            _reject(key + " must be an independent value")
        values[key] = _finite_positive(params[key]["value"], key)
    height = params["height"]
    if height["value"] is not None or not isinstance(height["expression"], str):
        _reject("height must be the derived relation")
    try:
        actual = ast.dump(ast.parse(height["expression"], mode="eval"), include_attributes=False)
        expected = ast.dump(ast.parse("width * 2 / 3", mode="eval"), include_attributes=False)
    except (SyntaxError, ValueError) as exc:
        raise UnsupportedPlan("invalid height relation") from exc
    if actual != expected:
        _reject("only height = width * 2 / 3 is supported")
    values["edit_x"] = _finite_positive(edit_x, "edit_x")
    values["edit_width"] = _finite_positive(edit_width, "edit_width")
    if abs(values["x"] - values["edit_x"]) <= 1e-4 or abs(values["width"] - values["edit_width"]) <= 1e-4:
        _reject("each edit must change its original value by more than the geometric check tolerance")
    for x in (values["x"], values["edit_x"]):
        for width in (values["width"], values["edit_width"]):
            if not all(math.isfinite(q) for q in (x + width, width * 2 / 3, values["y"] + width * 2 / 3)):
                _reject("derived geometry is non-finite")
    return values


def _number(value):
    # C# numeric literals are emitted from validated finite Python numbers only.
    text = format(value, ".17g")
    return text if any(ch in text for ch in ".eE") else text + ".0"


def render_journal(values):
    code = _JOURNAL_TEMPLATE
    for key, value in values.items():
        marker = "@T11_" + key.upper() + "@"
        if code.count(marker) != 1:
            raise RuntimeError("invalid internal template: " + marker)
        code = code.replace(marker, _number(value))
    if "@T11_" in code:
        raise RuntimeError("unresolved internal template marker")
    return code


def prepare(plan, output, edit_x, edit_width):
    """Create a new output directory; never overwrite and never launch NX."""
    values = map_plan(plan, edit_x, edit_width)
    journal = render_journal(values)
    target = Path(output).absolute()
    target.mkdir(parents=False, exist_ok=False)
    try:
        (target / "T11Journal.cs").write_text(journal, encoding="utf-8")
        (target / "input.json").write_text(json.dumps({"schema":"T11-P2-1", "plan":plan.to_dict(), "mapped_inputs_mm":values, "preparation_status":"generated_only"}, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (target / "Run.ps1").write_text(_RUNNER, encoding="utf-8")
    except BaseException:
        # Retain partial output; a new path is required, no automatic replay.
        raise
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--edit-x", required=True, type=float)
    parser.add_argument("--edit-width", required=True, type=float)
    args = parser.parse_args(argv)
    plan = Plan.from_json(Path(args.plan).read_text(encoding="utf-8-sig"))
    target = prepare(plan, args.output, args.edit_x, args.edit_width)
    print("Generated only; NX has not run. Output:", target)



_JOURNAL_TEMPLATE = r'''using System;
using System.IO;
using System.Globalization;
using NXOpen;
using NXOpen.Features;
using NXOpen.UF;
using NXOpen.GeometricUtilities;

// T06 standalone NX11 C# journal. Output is append-only and checkpointed.
public class T11Journal {
 static readonly double Depth = @T11_DEPTH@;
 static string evidence, stage="entry";
 public static bool IsSupportedRuntime(string release,string assemblyVersion) { return release == "NX V11.0" && assemblyVersion == "11.0.0.33"; }
 static string E(string s) { return (s??"").Replace("\\","\\\\").Replace("\t","\\t").Replace("\r","\\r").Replace("\n","\\n"); }
 static string N(double x) { return x.ToString("R", CultureInfo.InvariantCulture); }
 static void Log(string kind,string detail) { File.AppendAllText(evidence,E(kind)+"\t"+E(detail)+"\n"); }
 static void Step(string name) { stage=name; Log("checkpoint",name+" begin"); }
 static string SafeMessage(string message) {
  if(String.IsNullOrEmpty(message)) return "[empty]";
  if(System.Text.RegularExpressions.Regex.IsMatch(message,@"(?i)licen[cs]e|许可|授权|证书|密钥|server|服务器|password|passwd|secret|token|credential|splm|flex|https?://|\\|/|@|[A-Z]:")) return "[redacted: possible configuration or credential]";
  return message.Length>500 ? message.Substring(0,500)+" [truncated]" : message;
 }
 static void Need(bool x,string why) { if(!x) { Log("assertion_failure",why); throw new InvalidOperationException(why); } }
 static Point3d P(double x,double y,double z) {return new Point3d(x,y,z);}
 static Sketch.ConstraintGeometry C(NXObject o,Sketch.ConstraintPointType t) {return new Sketch.ConstraintGeometry(o,t,0);}
 static Sketch.DimensionGeometry D(NXObject o,Sketch.AssocType a) {return new Sketch.DimensionGeometry { Geometry=o,AssocType=a,AssocValue=0};}
 static SketchDimensionalConstraint Dim(Part p,Sketch s,Sketch.ConstraintType type,Sketch.DimensionGeometry a,Sketch.DimensionGeometry b,Point3d where,string name) {
  Step("sketch.dimension."+name+".create"); SketchDimensionalConstraint d=s.CreateDimension(type,a,b,where,null,Sketch.DimensionOption.CreateAsDriving);
  Need(d!=null && d.AssociatedExpression!=null,"dimension lacks expression: "+name);
  Step("sketch.dimension."+name+".rename"); p.Expressions.Rename(d.AssociatedExpression,name); return d;
 }
 static void Update(Session s,string name) { Session.UndoMarkId m=s.SetUndoMark(Session.MarkVisibility.Invisible,name); int n=s.UpdateManager.DoUpdate(m); Log("update",name+" errors="+n); Need(n==0,"update errors"); }
 static string F(Feature f) { return f.FeatureType+"/"+f.JournalIdentifier; }
 static void Snapshot(Part p,string label,double[] expected) {
  Sketch[] sketches=p.Sketches.ToArray(); Need(sketches.Length==1,"expected one sketch"); Sketch s=sketches[0];
  int dof; Sketch.Status status=s.GetStatus(out dof); Log(label+".sketch", "status="+status+" dof="+dof+" feature="+F(s.Feature));
  NXObject[] geometry=s.GetAllGeometry(); Need(geometry.Length==5,"expected four curves and one fixed datum point");
  foreach(NXObject o in geometry) { Line l=o as Line; if(l==null) { Need(o is NXOpen.Point,"unexpected sketch geometry"); Log(label+".datum_point",o.JournalIdentifier); continue; } Point3d a=l.StartPoint,b=l.EndPoint; Log(label+".line",l.JournalIdentifier+" ["+N(a.X)+","+N(a.Y)+","+N(a.Z)+"] ["+N(b.X)+","+N(b.Y)+","+N(b.Z)+"]"); }
  SketchConstraint[] cs=s.GetAllConstraintsOfType(Sketch.ConstraintClass.Any,Sketch.ConstraintType.NoCon); int count=0; bool[] seen=new bool[4];
  foreach(SketchConstraint c in cs) { SketchDimensionalConstraint d=c as SketchDimensionalConstraint; if(d==null) continue; Expression e=d.AssociatedExpression; Need(e!=null,"no expression"); count++;
   string users=""; foreach(Feature u in e.GetUsingFeatures()) users+=F(u)+";";
   string attached=""; bool hasLine=false; foreach(Sketch.DimensionGeometry g in d.GetDimensionGeometry()) { attached+=(g.Geometry==null?"null":g.Geometry.JournalIdentifier)+":"+g.AssocType+";"; if(g.Geometry is Line) hasLine=true; }
   Log(label+".dimension",e.Name+" value="+N(e.Value)+" rhs="+e.RightHandSide+" state="+d.DimensionState+" type="+d.ConstraintType+" geometry="+attached+" using_features="+users);
   Need(d.DimensionState==SketchDimensionalConstraint.DimensionStateType.Driving,"dimension not driving");
   int i=Array.IndexOf(new string[]{"probe_x","probe_y","probe_width","probe_height"},e.Name); Need(i>=0,"unexpected dimension"); Need(!seen[i],"duplicate dimension"); seen[i]=true; Need(hasLine,"dimension does not report line geometry"); Need(users.Length>0,"expression reports no using feature"); if(i==3) Need(e.RightHandSide.Replace(" ","")=="probe_width*2/3","height relationship missing"); Need(Math.Abs(e.Value-expected[i])<1e-5,"expression mismatch "+e.Name);
  }
  Need(count==4,"expected four dimensions"); Need(dof==0,"sketch not fully constrained");
  int extrudes=0; bool sketchParent=false; foreach(Feature f in p.Features) { string parents=""; foreach(Feature q in f.GetParents()) { parents+=F(q)+";"; if(f is Extrude && q.Tag.Equals(s.Feature.Tag)) sketchParent=true; } Log(label+".feature",F(f)+" parents="+parents); if(f is Extrude) extrudes++; }
  Need(extrudes==1,"expected one extrude"); Need(sketchParent,"extrude does not report sketch feature parent"); Body[] bodies=p.Bodies.ToArray(); Need(bodies.Length==1 && bodies[0].IsSolidBody,"expected one solid"); double[] box=new double[6]; UFSession.GetUFSession().Modl.AskBoundingBox(bodies[0].Tag,box);
  Log(label+".bbox_mm",String.Join(",",Array.ConvertAll(box,N))); double[] target={expected[0],expected[1],0,expected[0]+expected[2],expected[1]+expected[3],Depth}; for(int i=0;i<6;i++) Need(Math.Abs(box[i]-target[i])<1e-4,"bounding box mismatch index "+i);
 }
 public static void Main(string[] args) {
  evidence=Environment.GetEnvironmentVariable("T06_EVIDENCE"); string path=Environment.GetEnvironmentVariable("T06_MODEL");
  if(String.IsNullOrEmpty(evidence)||String.IsNullOrEmpty(path)||!File.Exists(evidence)||File.Exists(path)) throw new InvalidOperationException("invalid or occupied paths");
  try {
   stage="native_environment"; Session session=Session.GetSession(); UFSession uf=UFSession.GetUFSession(); string release; uf.UF.GetRelease(out release);
   Log("native_release",release); Log("language_env",Environment.GetEnvironmentVariable("UGII_LANG")); Log("journal_language","C# NXOpen"); Log("nxopen_assembly",typeof(Session).Assembly.FullName+" location="+typeof(Session).Assembly.Location); System.Diagnostics.FileVersionInfo ver=System.Diagnostics.FileVersionInfo.GetVersionInfo(typeof(Session).Assembly.Location); Log("nxopen_file_version", "file="+ver.FileVersion+" product="+ver.ProductVersion); Log("license_observation","NX session established; subsequent operation checkpoints record actual availability, no license feature or server identity inferred");
   Need(IsSupportedRuntime(release,typeof(Session).Assembly.GetName().Version.ToString()) && ver.FileVersion == "11.0.0.33" && ver.ProductVersion == "11.0.0.33" && Environment.GetEnvironmentVariable("UGII_LANG") == "simpl_chinese", "runtime differs from observed NX V11.0 C# profile");
   double x=@T11_X@, y=@T11_Y@, width=@T11_WIDTH@, editX=@T11_EDIT_X@, editWidth=@T11_EDIT_WIDTH@; double height=width*2.0/3.0; Need(session.Parts.Work==null && session.Parts.Display==null,"session is not blank");
   stage="new_part"; Part p=session.Parts.NewDisplay(path,Part.Units.Millimeters); Log("new_part","created millimeter blank "+path);
   Point3d zero=P(0,0,0); Vector3d normal=new Vector3d(0,0,1),axis=new Vector3d(1,0,0);
   Step("sketch.plane.create"); Plane plane=p.Planes.CreatePlane(zero,normal,SmartObject.UpdateOption.WithinModeling);
   Step("sketch.axis.create"); Direction direction=p.Directions.CreateDirection(zero,axis,SmartObject.UpdateOption.WithinModeling);
   Step("sketch.origin.create"); NXOpen.Point origin=p.Points.CreatePoint(zero);
   Step("sketch.builder.create"); SketchInPlaceBuilder sb=p.Sketches.CreateSketchInPlaceBuilder2(null);
   Step("sketch.builder.plane"); sb.PlaneReference=plane; Step("sketch.builder.axis"); sb.AxisReference=direction;
   Step("sketch.builder.origin"); sb.SketchOrigin=origin; Step("sketch.builder.plane_option"); sb.PlaneOption=Sketch.PlaneOption.ExistingPlane;
   Step("sketch.builder.origin_option"); sb.OriginOption=OriginMethod.SpecifyPoint; Step("sketch.builder.commit"); Sketch sk=(Sketch)sb.Commit();
   Step("sketch.builder.destroy"); sb.Destroy(); Step("sketch.activate"); sk.Activate(Sketch.ViewReorient.False);
   Line[] lines=new Line[4]; Step("sketch.line.0.create"); lines[0]=p.Curves.CreateLine(P(x,y,0),P(x+width,y,0));
   Step("sketch.line.1.create"); lines[1]=p.Curves.CreateLine(P(x+width,y,0),P(x+width,y+height,0));
   Step("sketch.line.2.create"); lines[2]=p.Curves.CreateLine(P(x+width,y+height,0),P(x,y+height,0));
   Step("sketch.line.3.create"); lines[3]=p.Curves.CreateLine(P(x,y+height,0),P(x,y,0));
   for(int i=0;i<4;i++) { Step("sketch.line."+i+".add"); sk.AddGeometry(lines[i],Sketch.InferConstraintsOption.InferNoConstraints); }
   for(int i=0;i<4;i++) { Step("sketch.coincident."+i); sk.CreateCoincidentConstraint(C(lines[i],Sketch.ConstraintPointType.EndVertex),C(lines[(i+1)%4],Sketch.ConstraintPointType.StartVertex)); }
   Step("sketch.horizontal.0"); sk.CreateHorizontalConstraint(C(lines[0],Sketch.ConstraintPointType.None)); Step("sketch.vertical.1"); sk.CreateVerticalConstraint(C(lines[1],Sketch.ConstraintPointType.None)); Step("sketch.horizontal.2"); sk.CreateHorizontalConstraint(C(lines[2],Sketch.ConstraintPointType.None)); Step("sketch.vertical.3"); sk.CreateVerticalConstraint(C(lines[3],Sketch.ConstraintPointType.None));
   // C3 hypothesis: midpoint is accepted for a fixed point, as used with the
   // newer M3 sketch-origin point. NX11 docs only explicitly define midpoint
   // for curves; the actual failing C2 call was not checkpointed.
   Step("sketch.anchor.create"); NXOpen.Point anchor=p.Points.CreatePoint(zero); Step("sketch.anchor.add"); sk.AddGeometry(anchor,Sketch.InferConstraintsOption.InferNoConstraints); Step("sketch.anchor.fix"); sk.CreateFixedConstraint(C(anchor,Sketch.ConstraintPointType.None)); Sketch.DimensionGeometry org=D(anchor,Sketch.AssocType.Midpoint),start=D(lines[0],Sketch.AssocType.StartPoint);
   SketchDimensionalConstraint dx=Dim(p,sk,Sketch.ConstraintType.HorizontalDim,org,start,P(x+5,y-2,0),"probe_x"),dy=Dim(p,sk,Sketch.ConstraintType.VerticalDim,org,start,P(x-2,y+2,0),"probe_y"),dw=Dim(p,sk,Sketch.ConstraintType.HorizontalDim,start,D(lines[0],Sketch.AssocType.EndPoint),P(x+width/2,y-3,0),"probe_width"),dh=Dim(p,sk,Sketch.ConstraintType.VerticalDim,D(lines[3],Sketch.AssocType.StartPoint),D(lines[3],Sketch.AssocType.EndPoint),P(x-3,y+height/2,0),"probe_height");
   Step("sketch.height.formula"); dh.AssociatedExpression.RightHandSide="probe_width*2/3"; Step("sketch.update"); sk.Update(); Step("sketch.deactivate"); sk.Deactivate(Sketch.ViewReorient.False,Sketch.UpdateLevel.Model); Step("sketch.model_update"); Update(session,"create sketch"); Log("sketch_created","four dimensions and constraints committed");
   stage="extrude"; Section section=p.Sections.CreateSection(0.0095,0.01,0.5); CurveFeatureRule rule=p.ScRuleFactory.CreateRuleCurveFeature(new Feature[]{sk.Feature}); section.SetAllowedEntityTypes(Section.AllowTypes.OnlyCurves); section.SetAllowRefCrvs(false); section.AddToSection(new SelectionIntentRule[]{rule},lines[0],null,null,zero,Section.Mode.Create,true);
   ExtrudeBuilder eb=p.Features.CreateExtrudeBuilder(null); eb.Section=section; eb.Direction=p.Directions.CreateDirection(zero,normal,SmartObject.UpdateOption.WithinModeling); eb.FeatureOptions.BodyType=FeatureOptions.BodyStyle.Solid; eb.Limits.StartExtend.Value.RightHandSide="0"; eb.Limits.EndExtend.Value.RightHandSide=N(Depth); eb.BooleanOperation.Type=BooleanOperation.BooleanType.Create; Feature extrude=eb.CommitFeature(); eb.Destroy(); Need(extrude!=null,"no extrude"); Update(session,"extrude"); Snapshot(p,"before_edit",new double[]{x,y,width,height});
   stage="edit_width"; dw.AssociatedExpression.RightHandSide=N(editWidth); Update(session,"edit width"); Snapshot(p,"after_width",new double[]{x,y,editWidth,editWidth*2.0/3.0});
   stage="edit_x"; dx.AssociatedExpression.RightHandSide=N(editX); Update(session,"edit x"); Snapshot(p,"after_position",new double[]{editX,y,editWidth,editWidth*2.0/3.0});
   stage="save"; using(PartSaveStatus save=p.Save(BasePart.SaveComponents.True,BasePart.CloseAfterSave.False)) Need(save.NumberUnsavedParts==0 && save.NumberUnsavedObjects==0 && !uf.Part.IsModified(p.Tag),"save failed"); Log("saved",path);
   stage="close"; p.Close(BasePart.CloseWholeTree.False,BasePart.CloseModified.CloseModified,null); Need(session.Parts.Work==null && session.Parts.Display==null,"part still open"); Log("closed",path);
   stage="reopen"; PartLoadStatus load; Part reopened=session.Parts.OpenDisplay(path,out load); using(load) Need(load.NumberUnloadedParts==0,"unloaded part on reopen"); Log("reopened",path); Snapshot(reopened,"reopened",new double[]{editX,y,editWidth,editWidth*2.0/3.0});
   stage="final_close"; Need(!uf.Part.IsModified(reopened.Tag),"reopened part modified"); reopened.Close(BasePart.CloseWholeTree.False,BasePart.CloseModified.CloseModified,null); Log("result","PASS: T11 IR fixture, separate width and position edits, native readback and reopen; license scope is observed operations only");
  } catch(Exception ex) { Log("failure","stage="+stage+" type="+ex.GetType().FullName+" nx_error="+(ex is NXException?((NXException)ex).ErrorCode.ToString(CultureInfo.InvariantCulture):"none")+" message="+SafeMessage(ex.Message)+"; state may be unknown; do not replay automatically"); }
 }
 public static int GetUnloadOption(string arg) {return (int)Session.LibraryUnloadOption.Immediately;}
}





'''


_RUNNER = r'''$ErrorActionPreference = 'Stop'
$runner='C:\0sf\NX11\NXBIN\run_journal.exe'
$journal=Join-Path $PSScriptRoot 'T11Journal.cs'
if (!(Test-Path -LiteralPath $runner -PathType Leaf) -or !(Test-Path -LiteralPath $journal -PathType Leaf)) { throw 'Missing NX11 runner or journal.' }
$busy=@(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -in @('ugraf','run_journal','M2JsonlHelper') })
if ($busy.Count -ne 0) { throw 'NX/Journal/helper is active; stop and return to root queue.' }
$model=Join-Path $PSScriptRoot 't11-blank.prt'
$evidence=Join-Path $PSScriptRoot 'native-evidence.tsv'
$stdout=Join-Path $PSScriptRoot 'runner-stdout.txt'
$stderr=Join-Path $PSScriptRoot 'runner-stderr.txt'
$claim=Join-Path $PSScriptRoot 'claim.txt'
foreach($path in @($model,$evidence,$stdout,$stderr,$claim)) { if(Test-Path -LiteralPath $path) { throw 'Output already exists; stop, no replay.' } }
$stream=[IO.File]::Open($claim,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None); $stream.Dispose()
$stream=[IO.File]::Open($evidence,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read); $stream.Dispose()
$vars=@('UGII_BASE_DIR','UGII_ROOT_DIR','PATH','T06_EVIDENCE','T06_MODEL'); $previous=@{}
foreach($name in $vars) { $previous[$name]=[Environment]::GetEnvironmentVariable($name,'Process') }
try {
 [Environment]::SetEnvironmentVariable('UGII_BASE_DIR','C:\0sf\NX11','Process')
 [Environment]::SetEnvironmentVariable('UGII_ROOT_DIR','C:\0sf\NX11\UGII','Process')
 [Environment]::SetEnvironmentVariable('PATH','C:\0sf\NX11\NXBIN;C:\0sf\NX11\UGII;'+$previous['PATH'],'Process')
 [Environment]::SetEnvironmentVariable('T06_EVIDENCE',$evidence,'Process')
 [Environment]::SetEnvironmentVariable('T06_MODEL',$model,'Process')
 [IO.File]::WriteAllLines($claim,@('T11-P2-1',('start: '+[DateTimeOffset]::Now.ToString('o')),('cwd: '+(Get-Location).Path),('runner: '+$runner),('journal: '+$journal),('UGII_LANG: '+$env:UGII_LANG),'License inherited; values excluded. Exit code is not evidence.'))
 & $runner $journal 1> $stdout 2> $stderr
 $code=$LASTEXITCODE
 [IO.File]::AppendAllText($claim,"`nrunner exit code: $code`nend: $([DateTimeOffset]::Now.ToString('o'))`n")
 Write-Output "Runner returned $code. Inspect native-evidence.tsv and logs; missing PASS or any failure is not success. Do not replay automatically."
} finally { foreach($name in $vars) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') } }
'''

if __name__ == "__main__":
    main()
