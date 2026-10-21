import {startReportNotices} from './report-notices.js';
import {requirePageAccount} from './page-session.js';
await requirePageAccount('USER');
startReportNotices();
