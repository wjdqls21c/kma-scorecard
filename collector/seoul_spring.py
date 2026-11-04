"""Use verified checkpoint retries for new month collections."""
import seoul_month as m
from seoul_month_recovery import save_checkpoint
if __name__=="__main__":
    m.git_save=save_checkpoint
    m.main()
