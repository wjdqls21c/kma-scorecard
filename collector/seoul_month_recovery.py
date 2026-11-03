"""Keep local checkpoints even if GitHub push temporarily fails."""
import os,subprocess,time
import seoul_month as m
def save_checkpoint(day):
    if not os.environ.get("GITHUB_ACTIONS"):return True
    try:
        subprocess.run(["git","add",str(m.DIR.relative_to(m.ROOT))],cwd=m.ROOT,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if subprocess.run(["git","diff","--cached","--quiet"],cwd=m.ROOT).returncode:
            subprocess.run(["git","commit","-m",f"Checkpoint Seoul {m.MONTH_KEY} day {day:02}"],cwd=m.ROOT,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for attempt in range(3):
            result=subprocess.run(["git","push","origin","HEAD:"+m.BRANCH],cwd=m.ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            if result.returncode==0:return True
            print("CHECKPOINT_PUSH_RETRY "+str(attempt+1),flush=True)
            time.sleep(2*(attempt+1))
    except subprocess.CalledProcessError:
        print("CHECKPOINT_LOCAL_GIT_FAILURE files retained for artifact",flush=True)
    print("CHECKPOINT_PUSH_DEFERRED local files retained; collection continues",flush=True)
    return False
def main():
    base=m.summary
    def report():
        r=base()
        r["recoverySourceRun"]=41562542364
        r["usageComplete"]=False
        r["limitations"].append("Usage counts cover persisted checkpoints only; the interrupted prior run may have unrecorded attempts.")
        return r
    m.git_save=save_checkpoint
    m.summary=report
    m.main()
if __name__=="__main__":main()
